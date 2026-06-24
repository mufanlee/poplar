import re

with open('/tmp/poplar-screen.log', 'rb') as f:
    data = f.read()

text = data.decode('utf-8', errors='replace')

# Find the last ChatView header position
last_header = text.rfind('╭─────────────────────────────────────────────────────────────────────────╮')
if last_header < 0:
    last_header = text.rfind('╭─')

# Get the section from last ChatView header to end
section = text[last_header:]

# Count Assistant labels in last frame
assistant_count = section.count('> 🤖 Assistant')
tool_count = section.count('🔧')
user_count = section.count('> 👤 You')

print(f"Final frame: User={user_count}, Assistant={assistant_count}, Tool={tool_count}")

# Show the assistant label lines
for line in section.split('\n'):
    clean = line
    # Strip ANSI codes
    clean = re.sub(r'\x1b\[[0-9;]*m', '', clean)
    if 'Assistant' in clean or '👤 You' in clean or '🔧' in clean:
        print(clean.strip()[:80])
