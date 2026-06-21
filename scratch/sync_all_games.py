import json
import os
import re

# We will read the existing games from src/all68GamesData.ts, keeping metadata
# but replacing the 'initial' and 'moves' fields with the correct ones from the parsed JSON files.

def parse_compact_games_raw():
    filepath = '/Users/lfesch/work_files/chess/src/all68GamesData.ts'
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Let's find the COMPACT_68_GAMES array
    start_match = re.search(r'export const COMPACT_68_GAMES: CompactIllustrativeGame\[\] = \[', content)
    if not start_match:
        print("Could not find COMPACT_68_GAMES in all68GamesData.ts")
        return []
    
    start_idx = start_match.end()
    game_blocks = []
    depth = 0
    
    i = start_idx
    while i < len(content):
        char = content[i]
        if char == '[':
            depth += 1
        elif char == ']':
            depth -= 1
            if depth < 0:
                break
        
        if char == '{' and depth == 0:
            obj_depth = 1
            obj_chars = [char]
            i += 1
            while i < len(content) and obj_depth > 0:
                c = content[i]
                if c == '{':
                    obj_depth += 1
                elif c == '}':
                    obj_depth -= 1
                obj_chars.append(c)
                i += 1
            game_blocks.append("".join(obj_chars))
            continue
        i += 1
    
    games = []
    for block in game_blocks:
        num_m = re.search(r'num:\s*(\d+)', block)
        white_m = re.search(r'white:\s*["\'](.*?)["\']', block)
        black_m = re.search(r'black:\s*["\'](.*?)["\']', block)
        event_m = re.search(r'event:\s*["\'](.*?)["\']', block)
        year_m = re.search(r'year:\s*(\d+)', block)
        chapter_m = re.search(r'chapter:\s*(\d+)', block)
        chapterTitle_m = re.search(r'chapterTitle:\s*["\'](.*?)["\']', block)
        page_m = re.search(r'page:\s*(\d+)', block)
        initial_m = re.search(r'initial:\s*["\'](.*?)["\']', block)
        
        if not num_m:
            continue
            
        games.append({
            "num": int(num_m.group(1)),
            "white": white_m.group(1) if white_m else "",
            "black": black_m.group(1) if black_m else "",
            "event": event_m.group(1) if event_m else "",
            "year": int(year_m.group(1)) if year_m else 0,
            "chapter": int(chapter_m.group(1)) if chapter_m else 0,
            "chapterTitle": chapterTitle_m.group(1) if chapterTitle_m else "",
            "page": int(page_m.group(1)) if page_m else 0,
            "initial": initial_m.group(1) if initial_m else "",
            "raw_block": block
        })
    return games

# Load all parsed games from JSON files
def load_parsed_games():
    directory = '/Users/lfesch/work_files/chess'
    parsed_games = {}
    
    for filename in os.listdir(directory):
        if filename.startswith('parsed_pages_') and filename.endswith('.json'):
            filepath = os.path.join(directory, filename)
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                exercises = data.get('exercises', [])
                for ex in exercises:
                    preparsed = ex.get('preparsedJson', {})
                    if not preparsed:
                        continue
                    
                    game_id = preparsed.get('game_id', '')
                    title = ex.get('title', '')
                    
                    game_num = None
                    num_match = re.search(r'Game\s*(\d+)', title, re.IGNORECASE)
                    if num_match:
                        game_num = int(num_match.group(1))
                    elif game_id.startswith('game_'):
                        num_match_id = re.search(r'game_(\d+)', game_id)
                        if num_match_id:
                            game_num = int(num_match_id.group(1))
                    
                    if game_num is None:
                        continue
                        
                    parsed_games[game_num] = {
                        "id": ex.get('id'),
                        "title": title,
                        "white": preparsed.get('white', ''),
                        "black": preparsed.get('black', ''),
                        "initial_moves": preparsed.get('initial_moves', ''),
                        "moves": preparsed.get('interactive_section', {}).get('moves', []),
                        "file": filename
                    }
            except Exception as e:
                print(f"Error reading {filename}: {e}")
    return parsed_games

def main():
    compact_games = parse_compact_games_raw()
    parsed_games = load_parsed_games()
    
    print(f"Loaded {len(compact_games)} games from all68GamesData.ts")
    print(f"Loaded {len(parsed_games)} games from parsed JSON files")
    
    synced_games = []
    missing_count = 0
    
    for cg in compact_games:
        num = cg['num']
        pg = parsed_games.get(num)
        
        # If not found by number, try player names
        if not pg:
            for g_num, g_data in parsed_games.items():
                if cg['white'].lower() in g_data['white'].lower() and cg['black'].lower() in g_data['black'].lower():
                    pg = g_data
                    print(f"Matched Game {num} to parsed game by players: {cg['white']} vs {cg['black']}")
                    break
        
        if not pg:
            print(f"WARNING: Game {num} ({cg['white']} vs {cg['black']}) not found in parsed JSONs! Keeping original.")
            # Reconstruct original moves list
            # We can parse the original moves from the raw block
            moves = []
            moves_match = re.search(r'moves:\s*\[(.*?)\]', cg['raw_block'], re.DOTALL)
            if moves_match:
                moves_content = moves_match.group(1)
                move_objs = re.findall(r'\{\s*m:\s*["\'](.*?)["\']\s*,\s*c:\s*["\'](.*?)["\']\s*\}', moves_content, re.DOTALL)
                for m, c in move_objs:
                    moves.append({"m": m, "c": c})
            
            synced_games.append({
                "num": num,
                "white": cg['white'],
                "black": cg['black'],
                "event": cg['event'],
                "year": cg['year'],
                "chapter": cg['chapter'],
                "chapterTitle": cg['chapterTitle'],
                "page": cg['page'],
                "initial": cg['initial'],
                "moves": moves
            })
            missing_count += 1
            continue
            
        # Format initial moves
        # In the parsed JSON, initial_moves might contain move numbers, e.g. "1 d4 Nf6 2 c4...".
        # Let's clean it up slightly if needed, or keep it as is. The validate_games.ts handles numbers,
        # but let's check what it looks like.
        initial = pg['initial_moves'].strip()
        # Clean double spaces
        initial = re.sub(r'\s+', ' ', initial)
        
        # Format interactive moves
        # In parsed JSON: [{ "move_number": 14, "player": "W", "move": "Nd2!", "commentary": "..." }]
        # In Compact: [{ m: "Nd2!", c: "..." }]
        moves = []
        for pm in pg['moves']:
            m_val = pm.get('move', '')
            c_val = pm.get('commentary', '')
            # Clean up quotes in commentary
            c_val = c_val.replace('"', '\\"')
            c_val = c_val.replace('\n', ' ')
            moves.append({
                "m": m_val,
                "c": c_val
            })
            
        synced_games.append({
            "num": num,
            "white": cg['white'],
            "black": cg['black'],
            "event": cg['event'],
            "year": cg['year'],
            "chapter": cg['chapter'],
            "chapterTitle": cg['chapterTitle'],
            "page": cg['page'],
            "initial": initial,
            "moves": moves
        })
        
    print(f"Successfully synchronized {len(synced_games) - missing_count} games.")
    
    # Now, write the synchronized games back to src/all68GamesData.ts!
    # We will generate the TypeScript code for the COMPACT_68_GAMES array.
    
    ts_code_lines = [
        "import { SampleBookPage, ParsedChessGame, ChessMove } from './types';",
        "",
        "export interface CompactIllustrativeGame {",
        "  num: number;",
        "  white: string;",
        "  black: string;",
        "  event: string;",
        "  year: number;",
        "  chapter: number;",
        "  chapterTitle: string;",
        "  page: number;",
        "  initial: string;",
        "  moves: Array<{ m: string; c: string }>; // Move symbol (SAN) and commentary",
        "}",
        "",
        "export const COMPACT_68_GAMES: CompactIllustrativeGame[] = ["
    ]
    
    for g in synced_games:
        ts_code_lines.append("  {")
        ts_code_lines.append(f"    num: {g['num']},")
        ts_code_lines.append(f"    white: \"{g['white']}\",")
        ts_code_lines.append(f"    black: \"{g['black']}\",")
        ts_code_lines.append(f"    event: \"{g['event']}\",")
        ts_code_lines.append(f"    year: {g['year']},")
        ts_code_lines.append(f"    chapter: {g['chapter']},")
        ts_code_lines.append(f"    chapterTitle: \"{g['chapterTitle']}\",")
        ts_code_lines.append(f"    page: {g['page']},")
        ts_code_lines.append(f"    initial: \"{g['initial']}\",")
        ts_code_lines.append("    moves: [")
        for m in g['moves']:
            ts_code_lines.append(f"      {{ m: \"{m['m']}\", c: \"{m['c']}\" }},")
        ts_code_lines.append("    ]")
        ts_code_lines.append("  },")
        
    ts_code_lines.append("];")
    ts_code_lines.append("")
    
    # Append the getFullIllustrativeGamesList function
    ts_code_lines.append("export function getFullIllustrativeGamesList(): SampleBookPage[] {")
    ts_code_lines.append("  return COMPACT_68_GAMES.map(g => {")
    ts_code_lines.append("    const movesList: ChessMove[] = [];")
    ts_code_lines.append("    const initialMovesList = g.initial ")
    ts_code_lines.append("      ? g.initial.strip ? g.initial.trim().split(/\\s+/).filter(token => !/^\\d+$/.test(token)) : g.initial.trim().split(/\\s+/).filter(token => !/^\\d+$/.test(token))")
    ts_code_lines.append("      : [];")
    # Let's write this function properly as it was in the original file
    # Wait, let's look at the original function in the file to make sure it's identical!
    # The original function in all68GamesData.ts is:
    # (let's check our view_file of all68GamesData.ts lines 1200-1258):
    #   return COMPACT_68_GAMES.map(g => {
    #     const movesList: ChessMove[] = [];
    #     const initialMovesList = g.initial 
    #       ? g.initial.trim().split(/\s+/).filter(token => !/^\d+$/.test(token)) 
    #       : [];
    #     const initialMovesCount = initialMovesList.length;
    #     let isWhiteTurn = initialMovesCount % 2 === 0;
    #     let currentMoveNumber = Math.floor(initialMovesCount / 2) + 1;
    #     const startingMove = currentMoveNumber;
    # 
    #     g.moves.forEach((mv, idx) => {
    #       movesList.push({
    #         move_number: currentMoveNumber,
    #         player: isWhiteTurn ? 'W' : 'B',
    #         move: mv.m,
    #         commentary: mv.c
    #       });
    # 
    #       if (!isWhiteTurn) {
    #         currentMoveNumber++;
    #       }
    #       isWhiteTurn = !isWhiteTurn;
    #     });
    # 
    #     const pageId = `game_${g.num}`;
    # 
    #     return {
    #       id: pageId,
    #       title: `Game ${g.num}: ${g.white} vs ${g.black} (${g.event} ${g.year})`,
    #       description: `Chapter ${g.chapter} (${g.chapterTitle}) • Page ${g.page}`,
    #       imageFilename: "chess_board.png",
    #       textContext: `Game ${g.num}\nWhite: ${g.white}\nBlack: ${g.black}\nEvent: ${g.event} ${g.year}\nPage: ${g.page}\n\nInitial Setup: ${g.initial}\n\nMoves:\n${g.moves.map((m, i) => `${i + 1}. ${m.m} - ${m.c}`).join('\\n')}`,
    #       preparsedJson: {
    #         game_id: pageId,
    #         white: g.white,
    #         black: g.black,
    #         event: `${g.event} ${g.year}`,
    #         initial_moves: g.initial,
    #         interactive_section: {
    #           starting_move: startingMove,
    #           moves: movesList
    #         }
    #       }
    #     };
    #   });
    # }
    
    # Let's write the exact function to avoid compile errors!
    ts_code_lines = [
        "import { SampleBookPage, ParsedChessGame, ChessMove } from './types';",
        "",
        "export interface CompactIllustrativeGame {",
        "  num: number;",
        "  white: string;",
        "  black: string;",
        "  event: string;",
        "  year: number;",
        "  chapter: number;",
        "  chapterTitle: string;",
        "  page: number;",
        "  initial: string;",
        "  moves: Array<{ m: string; c: string }>; // Move symbol (SAN) and commentary",
        "}",
        "",
        "export const COMPACT_68_GAMES: CompactIllustrativeGame[] = ["
    ]
    
    for g in synced_games:
        ts_code_lines.append("  {")
        ts_code_lines.append(f"    num: {g['num']},")
        ts_code_lines.append(f"    white: \"{g['white']}\",")
        ts_code_lines.append(f"    black: \"{g['black']}\",")
        ts_code_lines.append(f"    event: \"{g['event']}\",")
        ts_code_lines.append(f"    year: {g['year']},")
        ts_code_lines.append(f"    chapter: {g['chapter']},")
        ts_code_lines.append(f"    chapterTitle: \"{g['chapterTitle']}\",")
        ts_code_lines.append(f"    page: {g['page']},")
        ts_code_lines.append(f"    initial: \"{g['initial']}\",")
        ts_code_lines.append("    moves: [")
        for m in g['moves']:
            # Double-escape backslashes in comments
            escaped_c = m['c'].replace('\\', '\\\\')
            ts_code_lines.append(f"      {{ m: \"{m['m']}\", c: \"{escaped_c}\" }},")
        ts_code_lines.append("    ]")
        ts_code_lines.append("  },")
        
    ts_code_lines.append("];")
    ts_code_lines.append("")
    ts_code_lines.append("export function getFullIllustrativeGamesList(): SampleBookPage[] {")
    ts_code_lines.append("  return COMPACT_68_GAMES.map(g => {")
    ts_code_lines.append("    const movesList: ChessMove[] = [];")
    ts_code_lines.append("    const initialMovesList = g.initial")
    ts_code_lines.append("      ? g.initial.trim().split(/\\s+/).filter(token => !/^\\d+\\.?$/.test(token))")
    ts_code_lines.append("      : [];")
    ts_code_lines.append("    const initialMovesCount = initialMovesList.length;")
    ts_code_lines.append("    let isWhiteTurn = initialMovesCount % 2 === 0;")
    ts_code_lines.append("    let currentMoveNumber = Math.floor(initialMovesCount / 2) + 1;")
    ts_code_lines.append("    const startingMove = currentMoveNumber;")
    ts_code_lines.append("")
    ts_code_lines.append("    g.moves.forEach((mv, idx) => {")
    ts_code_lines.append("      movesList.push({")
    ts_code_lines.append("        move_number: currentMoveNumber,")
    ts_code_lines.append("        player: isWhiteTurn ? 'W' : 'B',")
    ts_code_lines.append("        move: mv.m,")
    ts_code_lines.append("        commentary: mv.c")
    ts_code_lines.append("      });")
    ts_code_lines.append("")
    ts_code_lines.append("      if (!isWhiteTurn) {")
    ts_code_lines.append("        currentMoveNumber++;")
    ts_code_lines.append("      }")
    ts_code_lines.append("      isWhiteTurn = !isWhiteTurn;")
    ts_code_lines.append("    });")
    ts_code_lines.append("")
    ts_code_lines.append("    const pageId = `game_${g.num}`;")
    ts_code_lines.append("")
    ts_code_lines.append("    return {")
    ts_code_lines.append("      id: pageId,")
    ts_code_lines.append("      title: `Game ${g.num}: ${g.white} vs ${g.black} (${g.event} ${g.year})`,")
    ts_code_lines.append("      description: `Chapter ${g.chapter} (${g.chapterTitle}) • Page ${g.page}`,")
    ts_code_lines.append("      imageFilename: \"chess_board.png\",")
    ts_code_lines.append("      textContext: `Game ${g.num}\\nWhite: ${g.white}\\nBlack: ${g.black}\\nEvent: ${g.event} ${g.year}\\nPage: ${g.page}\\n\\nInitial Setup: ${g.initial}\\n\\nMoves:\\n${g.moves.map((m, i) => `${i + 1}. ${m.m} - ${m.c}`).join('\\n')}`,")
    ts_code_lines.append("      preparsedJson: {")
    ts_code_lines.append("        game_id: pageId,")
    ts_code_lines.append("        white: g.white,")
    ts_code_lines.append("        black: g.black,")
    ts_code_lines.append("        event: `${g.event} ${g.year}`,")
    ts_code_lines.append("        initial_moves: g.initial,")
    ts_code_lines.append("        interactive_section: {")
    ts_code_lines.append("          starting_move: startingMove,")
    ts_code_lines.append("          moves: movesList")
    ts_code_lines.append("        }")
    ts_code_lines.append("      }")
    ts_code_lines.append("    };")
    ts_code_lines.append("  });")
    ts_code_lines.append("}")
    
    with open('/Users/lfesch/work_files/chess/src/all68GamesData.ts', 'w') as f:
        f.write("\n".join(ts_code_lines))
    print("TypeScript file written successfully!")

if __name__ == '__main__':
    main()
