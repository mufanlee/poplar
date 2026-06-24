import re

with open('/tmp/poplar-screen.log', 'rb') as f:
    data = f.read()

text = data.decode('utf-8', errors='replace')

# Split into frames by ChatView header
frames = text.split('\xe2\x95\xad\xe2\x94\x80' * 3)  # ╭───

for i, f in enumerate(frames[-5:]):
    a_count = f.count('Assistant')
    t_count = f.count('\xf0\x9f\x94\xa7')  # 🔧
    print(f"\nFrame {i}: Assistant={a_count}, Tool={t_count}")
    for line in f.split('\n'):
        if 'Assistant' in line or '\xf0\x9f\x94\xa7' in line:
            # Extract visible text
            idx = line.find('> ')
            if idx >= 0:
                snippet = line[idx:idx+40]
            else:
                snippet = line[:60]
            print(f"  {snippet.strip()}")
