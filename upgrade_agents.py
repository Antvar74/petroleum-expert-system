import os
import re

# Mapping of agent files to their documentation source
AGENT_MAPPING = {
    "agents/geologist.py": "docs/geologist-petrophysicist.md",
    "agents/hydrologist.py": "docs/hydrologist-pore-pressure-specialist.md",
    "agents/mud_engineer.py": "docs/mud-engineer-fluids-specialist.md",
    "agents/well_engineer.py": "docs/well-engineer-trajectory-specialist.md"
}

def upgrade_agent(agent_path, doc_path):
    print(f"Upgrading {agent_path} with content from {doc_path}...")
    
    # Read the documentation content
    with open(doc_path, 'r', encoding='utf-8') as f:
        doc_content = f.read()
    print(f"DEBUG: Read {len(doc_content)} chars from {doc_path}")
    
    # Read the agent code
    with open(agent_path, 'r', encoding='utf-8') as f:
        agent_code = f.read()
    print(f"DEBUG: Read {len(agent_code)} chars from {agent_path}")
    
    # Check if system_prompt exists
    pattern = r'(system_prompt\s*=\s*""")[\s\S]*?("""\s*\n)'
    match = re.search(pattern, agent_code)
    
    if not match:
        print(f"Error: Could not find system_prompt variable in {agent_path}")
        return False
        
    # Prepare the replacement
    # Escape triple quotes in doc content to prevent syntax errors
    if '"""' in doc_content:
        print(f"Warning: Triple quotes found in {doc_path}. Escaping them.")
        doc_content = doc_content.replace('"""', '\\"\\"\\"')
    
    # Replace the content using string slicing to avoid regex backslash issues
    # match.group(0) is the whole block: system_prompt = """..."""
    # match.group(1) is system_prompt = """
    # match.group(2) is """\n
    
    # We want to replace everything between group 1 and group 2 with doc_content
    # match.end(1) is the index after system_prompt = """
    # match.start(2) is the index before """\n
    
    new_code = agent_code[:match.end(1)] + doc_content + agent_code[match.start(2):]
    print(f"DEBUG: New code length: {len(new_code)}")
    
    # Write back
    with open(agent_path, 'w', encoding='utf-8') as f:
        f.write(new_code)
        
    print(f"Successfully upgraded {agent_path}")
    return True

def main():
    base_dir = os.getcwd()
    success_count = 0
    
    for agent_file, doc_file in AGENT_MAPPING.items():
        agent_path = os.path.join(base_dir, agent_file)
        doc_path = os.path.join(base_dir, doc_file)
        
        if os.path.exists(agent_path) and os.path.exists(doc_path):
            if upgrade_agent(agent_path, doc_path):
                success_count += 1
        else:
            print(f"Skipping {agent_file}: File or doc not found.")
            
    print(f"\nTotal agents upgraded: {success_count}/{len(AGENT_MAPPING)}")

if __name__ == "__main__":
    main()
