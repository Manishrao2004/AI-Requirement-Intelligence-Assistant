import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.graph import analysis_pipeline

def generate():
    try:
        print("Generating LangGraph workflow visualization...")
        # Get the compiled graph image bytes
        png_bytes = analysis_pipeline.get_graph().draw_mermaid_png()
        
        # Define output directory: root/assets/
        assets_dir = project_root / "assets"
        assets_dir.mkdir(exist_ok=True)
        
        output_file = assets_dir / "workflow_graph.png"
        with open(output_file, "wb") as f:
            f.write(png_bytes)
            
        print(f"Success! Generated '{output_file.relative_to(project_root)}'.")
    except Exception as e:
        print(f"Error generating graph: {e}")
        print("Make sure you have an active internet connection to render the Mermaid graph.")

if __name__ == "__main__":
    generate()
