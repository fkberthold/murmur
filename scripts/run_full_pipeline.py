#!/usr/bin/env python3
"""Run full pipeline and save output for review."""

import json
from pathlib import Path
from datetime import datetime
from murmur.executor import GraphExecutor
from murmur.graph import load_graph
from murmur.transformers import create_registry

# Load the no-tts-v2b graph (generates script but no audio)
graph = load_graph(Path('config/graphs/no-tts-v2b.yaml'))
registry = create_registry()

config = {
    'news_topics': [
        {'name': 'science', 'query': 'science discoveries breakthroughs', 'priority': 'medium'},
        {'name': 'technology', 'query': 'technology innovation software', 'priority': 'medium'},
        {'name': 'ai', 'query': 'artificial intelligence machine learning', 'priority': 'high'},
    ],
    'slack_config_path': 'config/slack.yaml',
    'mcp_config_path': '.mcp.json',
    'history_path': 'data/history.json',
    'narrator_style': 'conversational and warm',
    'target_duration': 5
}

executor = GraphExecutor(graph, registry, artifact_dir=Path('output'))
results = executor.execute(config)

# Save the generated script
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
output_dir = Path('output')
output_dir.mkdir(exist_ok=True)

script_path = output_dir / f'{timestamp}_script.txt'
json_path = output_dir / f'{timestamp}_full_output.json'

# Extract script from generate node (results is TransformerIO, access .data)
script = results.data.get('generate', {}).get('script', 'No script generated')

# Save readable script
with open(script_path, 'w') as f:
    f.write(script)

# Save full JSON output
with open(json_path, 'w') as f:
    json.dump(results.data, f, indent=2, default=str)

print(f'Script saved to: {script_path}')
print(f'Full output saved to: {json_path}')
print()
print('=' * 60)
print('GENERATED SCRIPT:')
print('=' * 60)
print(script)
