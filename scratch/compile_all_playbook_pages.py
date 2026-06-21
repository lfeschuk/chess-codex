import os
import json
import re

# Load games metadata from compile_all_games.py parsing logic
def parse_compact_games_metadata():
    filepath = '/Users/lfesch/work_files/chess/src/all68GamesData.ts'
    with open(filepath, 'r') as f:
        content = f.read()
    
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
    
    games_meta = []
    for block in game_blocks:
        num_m = re.search(r'num:\s*(\d+)', block)
        white_m = re.search(r'white:\s*["\'](.*?)["\']', block)
        black_m = re.search(r'black:\s*["\'](.*?)["\']', block)
        event_m = re.search(r'event:\s*["\'](.*?)["\']', block)
        year_m = re.search(r'year:\s*(\d+)', block)
        chapter_m = re.search(r'chapter:\s*(\d+)', block)
        chapter_title_m = re.search(r'chapterTitle:\s*["\'](.*?)["\']', block)
        page_m = re.search(r'page:\s*(\d+)', block)
        
        if not num_m:
            continue
            
        games_meta.append({
            "num": int(num_m.group(1)),
            "white": white_m.group(1) if white_m else "",
            "black": black_m.group(1) if black_m else "",
            "event": event_m.group(1) if event_m else "",
            "year": int(year_m.group(1)) if year_m else 0,
            "chapter": int(chapter_m.group(1)) if chapter_m else 1,
            "chapterTitle": chapter_title_m.group(1) if chapter_title_m else "",
            "page": int(page_m.group(1)) if page_m else 0
        })
    return games_meta

def main():
    # 1. Load games metadata
    games_meta = parse_compact_games_metadata()
    print(f"Loaded metadata for {len(games_meta)} illustrative games.")
    
    # Official Chapter Titles Registry
    CHAPTER_TITLES = {
        1: "Alternatives to 7 O-O",
        2: "7 O-O: Alternatives to 7...Nc6",
        3: "7 O-O Nc6: Main Line with 9 Ne1",
        4: "Alternatives to 9 Ne1",
        5: "The Sämisch Variation",
        6: "The Fianchetto Variation",
        7: "The Four Pawns Attack",
        8: "The Averbakh System",
        9: "White Plays h3",
        10: "Other Systems"
    }
    
    # Map from game number and player key to metadata
    game_by_num = {g['num']: g for g in games_meta}
    game_by_player = {f"{g['white'].lower()}_{g['black'].lower()}": g for g in games_meta}
    
    # 2. Load all parsed items from raw JSONs
    directory = '/Users/lfesch/work_files/chess'
    raw_items = []
    
    # Include both standard files and scratch/ files (for the new Petrosian and Gligoric)
    json_files = []
    for filename in os.listdir(directory):
        if filename.startswith('parsed_pages_') and filename.endswith('.json'):
            json_files.append(os.path.join(directory, filename))
            
    # Add new parsed files from scratch if they exist
    new_scratch_files = [
        'parsed_petrosian.json', 
        'parsed_gligoric.json',
        'parsed_chapter_2_theory.json',
        'parsed_chapter_3_g2g4.json',
        'parsed_chapter_3_10_be3.json',
        'parsed_chapter_4_9_nd2.json',
        'parsed_chapter_10_5_nge2.json'
    ]
    for new_file in new_scratch_files:
        new_path = os.path.join(directory, 'scratch', new_file)
        if os.path.exists(new_path):
            json_files.append(new_path)
            print(f"Including new parsed file: {new_file}")
            
    for filepath in json_files:
        filename = os.path.basename(filepath)
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # The new scratch files might have a direct exercise object or exercises array
            exercises = data.get('exercises', [])
            if not exercises and 'id' in data:
                exercises = [data] # Single item
                
            for idx, ex in enumerate(exercises):
                preparsed = ex.get('preparsedJson', {})
                if not preparsed:
                    continue
                
                ex_id = ex.get('id', '')
                title = ex.get('title', '')
                white = preparsed.get('white', 'Theory')
                black = preparsed.get('black', 'Theory')
                event = preparsed.get('event', '')
                
                # Determine type
                is_game = white != 'Theory' and black != 'Theory' and not ex_id.startswith('exercise')
                
                # Extract page range from filename
                range_match = re.search(r'parsed_pages_(\d+)_(\d+)\.json', filename)
                file_start_page = int(range_match.group(1)) if range_match else 1
                
                # Determine page and chapter
                item_page = None
                item_chapter = None
                item_chapter_title = ""
                
                # Try to match with illustrative game metadata
                game_meta = None
                game_num = None
                num_match = re.search(r'Game\s*(\d+)', title, re.IGNORECASE)
                if num_match:
                    game_num = int(num_match.group(1))
                elif ex_id.startswith('game_'):
                    num_match_id = re.search(r'game_(\d+)', ex_id)
                    if num_match_id:
                        game_num = int(num_match_id.group(1))
                
                if game_num and game_num in game_by_num:
                    game_meta = game_by_num[game_num]
                else:
                    player_key = f"{white.lower()}_{black.lower()}"
                    if player_key in game_by_player:
                        game_meta = game_by_player[player_key]
                
                if game_meta:
                    item_page = game_meta['page']
                    item_chapter = game_meta['chapter']
                    item_chapter_title = game_meta['chapterTitle']
                else:
                    # Parse page from title/description
                    page_match = re.search(r'Page\s*(\d+)', title + " " + ex.get('description', ''), re.IGNORECASE)
                    if page_match:
                        item_page = int(page_match.group(1))
                    else:
                        # Infer page based on filename and index in file
                        item_page = file_start_page + idx
                        
                    # Infer chapter from title or page
                    ch_match = re.search(r'Chapter\s*(\d+)', title + " " + event, re.IGNORECASE)
                    if ch_match:
                        item_chapter = int(ch_match.group(1))
                    else:
                        # Guess chapter based on page number
                        if item_page <= 25: item_chapter = 1
                        elif item_page <= 40: item_chapter = 2
                        elif item_page <= 60: item_chapter = 3
                        elif item_page <= 75: item_chapter = 4
                        elif item_page <= 100: item_chapter = 5
                        elif item_page <= 120: item_chapter = 6
                        elif item_page <= 135: item_chapter = 7
                        elif item_page <= 150: item_chapter = 8
                        elif item_page <= 160: item_chapter = 9
                        else: item_chapter = 10
                
                # Special overrides for our newly parsed files
                if filename == 'parsed_petrosian.json':
                    item_page = 16
                    item_chapter = 1
                elif filename == 'parsed_gligoric.json':
                    item_page = 21
                    item_chapter = 1
                elif filename == 'parsed_chapter_2_theory.json':
                    item_page = 33
                    item_chapter = 2
                elif filename == 'parsed_chapter_3_g2g4.json':
                    item_page = 48
                    item_chapter = 3
                elif filename == 'parsed_chapter_3_10_be3.json':
                    item_page = 52
                    item_chapter = 3
                elif filename == 'parsed_chapter_4_9_nd2.json':
                    item_page = 71
                    item_chapter = 4
                elif filename == 'parsed_chapter_10_5_nge2.json':
                    item_page = 167
                    item_chapter = 10
                
                # Resolve uniform chapter title globally
                item_chapter_title = CHAPTER_TITLES.get(item_chapter, "General & Tactics")
                
                raw_items.append({
                    "id": ex_id,
                    "title": title,
                    "description": ex.get('description', ''),
                    "imageFilename": ex.get('imageFilename', 'chess_board.png'),
                    "textContext": ex.get('textContext', ''),
                    "preparsedJson": preparsed,
                    "page": item_page,
                    "chapter": item_chapter,
                    "chapterTitle": item_chapter_title,
                    "is_game": is_game,
                    "moves_count": len(preparsed.get('interactive_section', {}).get('moves', []))
                })
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            
    # 3. Deduplicate by ID and Game Number, keeping the one with the most moves
    deduped = {}
    for item in raw_items:
        # Determine deduplication key
        key = item['id']
        if item['is_game'] and item.get('chapter') and item.get('page'):
            # If it's a game, try to key it by game number if possible, or by names
            game_num = None
            num_match = re.search(r'Game\s*(\d+)', item['title'], re.IGNORECASE)
            if num_match:
                game_num = int(num_match.group(1))
            
            if game_num:
                key = f"game_{game_num}"
            else:
                # Fallback to normalized player names
                white = item['preparsedJson'].get('white', '')
                black = item['preparsedJson'].get('black', '')
                if white and black:
                    key = f"game_{white.lower()}_{black.lower()}"
                    
        if key not in deduped:
            deduped[key] = item
        else:
            # Keep the one with more moves
            if item['moves_count'] > deduped[key]['moves_count']:
                deduped[key] = item
                
    items_list = list(deduped.values())
    print(f"Deduplicated to {len(items_list)} unique playable items.")
    
    # 4. Sort chronologically
    # Sorting key: Chapter -> Page -> Type order (theory before game, exercise at end) -> Title/ID
    def sorting_key(item):
        type_order = 0
        if not item['is_game'] and not item['id'].startswith('exercise'):
            type_order = 0 # Theory / Intro
        elif item['is_game']:
            type_order = 1 # Illustrative Game
        else:
            type_order = 2 # Exercise / puzzle
            
        return (item['chapter'], item['page'], type_order, item['id'])
        
    items_list.sort(key=sorting_key)
    
    # 5. Print sorted playbook list for verification
    print("\n--- CHRONOLOGICAL PLAYBOOK ---")
    for idx, item in enumerate(items_list):
        item_type = "Theory" if not item['is_game'] and not item['id'].startswith('exercise') else ("Game" if item['is_game'] else "Exercise")
        print(f"#{idx+1:03d} | Ch {item['chapter']} | Page {item['page']} | {item_type:8s} | {item['title'][:50]} (ID: {item['id']})")
        
    # 6. Generate TypeScript output
    ts_lines = []
    ts_lines.append("import { SampleBookPage } from './types';")
    ts_lines.append("")
    ts_lines.append("export const UNIFIED_PLAYBOOK_PAGES: SampleBookPage[] = [")
    
    for idx, item in enumerate(items_list):
        # Format a gorgeous description containing the chapter and page context
        ch_title = item['chapterTitle'] or "General & Tactics"
        ch_prefix = f"Chapter {item['chapter']} ({ch_title}) - Page {item['page']}. "
        
        # Strip any existing "Digitized from PDF chunk..." or "Chapter X" prefix from the description to avoid redundancy
        clean_desc = item['description']
        clean_desc = re.sub(r'^Digitized from PDF chunk.*?\.\s*', '', clean_desc)
        clean_desc = re.sub(r'^Chapter \d+ \(.*?\)\s*-\s*Page \d+\.\s*', '', clean_desc)
        
        desc = ch_prefix + clean_desc
        desc = desc.replace('"', '\\"').replace('\n', '\\n')
        text_ctx = item['textContext'].replace('"', '\\"').replace('\n', '\\n')
        
        preparsed_str = json.dumps(item['preparsedJson'], indent=4)
        # Indent the preparsed JSON string
        preparsed_indented = "\n".join("      " + line for line in preparsed_str.split("\n"))
        
        ts_lines.append("  {")
        ts_lines.append(f"    id: \"{item['id']}\",")
        ts_lines.append(f"    title: \"{item['title']}\",")
        ts_lines.append(f"    description: \"{desc}\",")
        ts_lines.append(f"    imageFilename: \"{item['imageFilename']}\",")
        ts_lines.append(f"    textContext: \"{text_ctx}\",")
        ts_lines.append("    preparsedJson: " + preparsed_indented.strip())
        
        if idx < len(items_list) - 1:
            ts_lines.append("  },")
        else:
            ts_lines.append("  }")
            
    ts_lines.append("];")
    
    output_path = '/Users/lfesch/work_files/chess/src/unifiedPlaybookData.ts'
    with open(output_path, 'w') as f:
        f.write("\n".join(ts_lines))
    print(f"\nSuccessfully compiled unified chronological database to {output_path}!")

if __name__ == '__main__':
    main()
