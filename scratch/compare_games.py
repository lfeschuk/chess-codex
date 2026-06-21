import json
import os
import re

# Load all 68 games from all68GamesData.ts
# Since it's typescript, we can extract the COMPACT_68_GAMES array using a regex or simple parser,
# or we can read a JSON representation if we have one.
# Wait, let's write a python parser to extract COMPACT_68_GAMES from src/all68GamesData.ts!
def parse_compact_games():
    filepath = '/Users/lfesch/work_files/chess/src/all68GamesData.ts'
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Let's find the COMPACT_68_GAMES array
    # It starts with 'export const COMPACT_68_GAMES: CompactIllustrativeGame[] = ['
    start_match = re.search(r'export const COMPACT_68_GAMES: CompactIllustrativeGame\[\] = \[', content)
    if not start_match:
        print("Could not find COMPACT_68_GAMES in all68GamesData.ts")
        return []
    
    start_idx = start_match.end()
    # Let's find the closing bracket '];' at the end of the array
    # Since the file ends with the export function, we can just find the matching bracket or parse it carefully
    # Let's parse it by finding each game object {...}
    game_blocks = []
    depth = 0
    current_block = []
    
    # We will scan from start_idx
    i = start_idx
    while i < len(content):
        char = content[i]
        if char == '[':
            depth += 1
        elif char == ']':
            depth -= 1
            if depth < 0:
                break
        
        # We want to extract each game object
        # A game object starts with '{' and ends with '}' at depth 1
        if char == '{' and depth == 0:
            # Start of game object
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
    
    # Now, let's convert each game block into a python dict
    # Since it's JS/TS, it might not be strict JSON (keys might not be quoted, double/single quotes, etc.)
    # We can use a simple parser or just evaluate/clean it.
    games = []
    for block in game_blocks:
        # Clean up the block to make it valid JSON if possible, or use a regex to extract fields
        # Fields: num, white, black, event, year, chapter, chapterTitle, page, initial, moves
        num_m = re.search(r'num:\s*(\d+)', block)
        white_m = re.search(r'white:\s*["\'](.*?)["\']', block)
        black_m = re.search(r'black:\s*["\'](.*?)["\']', block)
        event_m = re.search(r'event:\s*["\'](.*?)["\']', block)
        year_m = re.search(r'year:\s*(\d+)', block)
        page_m = re.search(r'page:\s*(\d+)', block)
        initial_m = re.search(r'initial:\s*["\'](.*?)["\']', block)
        
        if not num_m:
            continue
            
        num = int(num_m.group(1))
        white = white_m.group(1) if white_m else ""
        black = black_m.group(1) if black_m else ""
        event = event_m.group(1) if event_m else ""
        year = int(year_m.group(1)) if year_m else 0
        page = int(page_m.group(1)) if page_m else 0
        initial = initial_m.group(1) if initial_m else ""
        
        # Extract moves
        # moves is an array of { m: "...", c: "..." }
        moves = []
        moves_match = re.search(r'moves:\s*\[(.*?)\]', block, re.DOTALL)
        if moves_match:
            moves_content = moves_match.group(1)
            # Find all { m: "...", c: "..." } or {m:"...", c:"..."}
            move_objs = re.findall(r'\{\s*m:\s*["\'](.*?)["\']\s*,\s*c:\s*["\'](.*?)["\']\s*\}', moves_content, re.DOTALL)
            for m, c in move_objs:
                moves.append({"m": m, "c": c})
        
        games.append({
            "num": num,
            "white": white,
            "black": black,
            "event": event,
            "year": year,
            "page": page,
            "initial": initial,
            "moves": moves
        })
    return games

# Load all games from parsed_pages_*.json files
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
                    
                    # We can identify if it's an illustrative game
                    # Usually title starts with "Game" or id starts with "game_"
                    game_id = preparsed.get('game_id', '')
                    title = ex.get('title', '')
                    
                    # Let's extract game number if possible
                    game_num = None
                    num_match = re.search(r'Game\s*(\d+)', title, re.IGNORECASE)
                    if num_match:
                        game_num = int(num_match.group(1))
                    elif game_id.startswith('game_'):
                        num_match_id = re.search(r'game_(\d+)', game_id)
                        if num_match_id:
                            game_num = int(num_match_id.group(1))
                    
                    white = preparsed.get('white', '')
                    black = preparsed.get('black', '')
                    
                    # Reconstruct full move sequence
                    initial_moves_str = preparsed.get('initial_moves', '')
                    initial_moves = [re.sub(r'[!?]+$', '', m) for m in initial_moves_str.split() if m and not re.match(r'^\d+\.?$', m)]
                    
                    interactive_section = preparsed.get('interactive_section', {})
                    interactive_moves = []
                    if interactive_section:
                        for mv in interactive_section.get('moves', []):
                            interactive_moves.append(mv.get('move', ''))
                    
                    # Clean moves
                    def clean_move_list(moves):
                        cleaned = []
                        for m in moves:
                            # Skip move numbers if any
                            if re.match(r'^\d+\.?$', m):
                                continue
                            # Clean annotation suffixes
                            cleaned.append(re.sub(r'[!?]+$', '', m))
                        return cleaned
                    
                    # Reconstruct initial moves from string
                    # Split and filter out numbers
                    init_moves_tokens = initial_moves_str.split()
                    cleaned_init = []
                    for token in init_moves_tokens:
                        if re.match(r'^\d+\.?$', token):
                            continue
                        cleaned_init.append(re.sub(r'[!?]+$', '', token))
                        
                    cleaned_inter = clean_move_list(interactive_moves)
                    full_sequence = cleaned_init + cleaned_inter
                    
                    key = None
                    if game_num is not None:
                        key = game_num
                    else:
                        # Fallback to players
                        key = f"{white.lower()}_{black.lower()}"
                        
                    parsed_games[key] = {
                        "id": ex.get('id'),
                        "title": title,
                        "white": white,
                        "black": black,
                        "initial_moves": cleaned_init,
                        "interactive_moves": cleaned_inter,
                        "full_sequence": full_sequence,
                        "file": filename,
                        "preparsed": preparsed
                    }
            except Exception as e:
                print(f"Error reading {filename}: {e}")
    return parsed_games

def main():
    compact_games = parse_compact_games()
    parsed_games = load_parsed_games()
    
    output_lines = []
    output_lines.append(f"Parsed {len(compact_games)} games from all68GamesData.ts")
    output_lines.append(f"Loaded {len(parsed_games)} games from parsed JSON files")
    
    mismatches = []
    not_found = []
    valid_games_with_errors = [3, 11, 37, 38, 54, 68]
    
    for cg in compact_games:
        num = cg['num']
        parsed = parsed_games.get(num)
        if not parsed:
            match_found = False
            for pk, pg in parsed_games.items():
                if isinstance(pk, str) or isinstance(pk, int):
                    # Try name matching if key is not game number
                    pass
            # Try player name search
            for pg in parsed_games.values():
                if cg['white'].lower() in pg['white'].lower() and cg['black'].lower() in pg['black'].lower():
                    parsed = pg
                    break
            if not parsed:
                not_found.append(cg)
                continue
        
        cg_init_tokens = cg['initial'].split()
        cg_init = []
        for token in cg_init_tokens:
            if re.match(r'^\d+\.?$', token):
                continue
            cg_init.append(re.sub(r'[!?]+$', '', token))
            
        cg_inter = [re.sub(r'[!?]+$', '', m['m']) for m in cg['moves']]
        cg_full = cg_init + cg_inter
        
        pg_full = parsed['full_sequence']
        
        is_match = True
        min_len = min(len(cg_full), len(pg_full))
        
        for idx in range(min_len):
            if cg_full[idx] != pg_full[idx]:
                is_match = False
                break
                
        if not is_match:
            mismatches.append({
                "num": num,
                "white": cg['white'],
                "black": cg['black'],
                "reason": "Move sequence mismatch",
                "compact_seq": cg_full,
                "parsed_seq": pg_full,
                "file": parsed['file']
            })
        elif num in valid_games_with_errors:
            mismatches.append({
                "num": num,
                "white": cg['white'],
                "black": cg['black'],
                "reason": "Failed chess rules validator",
                "compact_seq": cg_full,
                "parsed_seq": pg_full,
                "file": parsed['file']
            })
            
    output_lines.append(f"\n--- COMPARISON RESULTS ---")
    output_lines.append(f"Total Mismatches/Errors Found: {len(mismatches)}")
    output_lines.append(f"Games Not Found in Parsed JSONs: {len(not_found)}")
    
    if not_found:
        output_lines.append("\nGames not found in parsed JSONs:")
        for g in not_found:
            output_lines.append(f"  Game {g['num']}: {g['white']} vs {g['black']} (Page {g['page']})")
            
    if mismatches:
        output_lines.append("\nMismatches and Validator Failures:")
        for m in mismatches:
            output_lines.append(f"\n* Game {m['num']}: {m['white']} vs {m['black']} ({m['reason']})")
            output_lines.append(f"  File: {m['file']}")
            comp_s = m['compact_seq']
            pars_s = m['parsed_seq']
            max_show = max(len(comp_s), len(pars_s))
            output_lines.append(f"  {'Index':<6} | {'COMPACT (App)':<15} | {'PARSED (Book JSON)':<15}")
            output_lines.append(f"  {'-'*44}")
            for idx in range(max_show):
                c_move = comp_s[idx] if idx < len(comp_s) else "-"
                p_move = pars_s[idx] if idx < len(pars_s) else "-"
                status = " " if c_move == p_move else "X"
                output_lines.append(f"  {idx:<6} | {c_move:<15} | {p_move:<15} {status}")

    # Write to file
    summary_path = '/Users/lfesch/work_files/chess/scratch/mismatches_summary.txt'
    with open(summary_path, 'w') as f:
        f.write("\n".join(output_lines))
    print(f"Comparison results written to {summary_path}")
    print(f"Total mismatches/errors: {len(mismatches)}")

if __name__ == '__main__':
    main()
