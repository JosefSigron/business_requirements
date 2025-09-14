import json
from pathlib import Path
from backend.services.parser import parse_structure_and_save, STRUCTURE_PATH

def main():
    src = '18-07-2022_4.2A.txt'
    parse_structure_and_save(src)
    data = json.loads(Path(STRUCTURE_PATH).read_text(encoding='utf-8'))
    for n in data:
        if n.get('id') == '8.5.9':
            print('8.5.9:', n.get('text'))
            break

if __name__ == '__main__':
    main()
