from fasthtml import ft
from op_tcg.frontend.utils.decklist import decklist_to_export_str, ensure_leader_id

def create_decklist_export_component(decklist: dict[str, int], leader_id: str, unique_id: str = "default"):
    """
    Create a reusable decklist export component with copy functionality.
    
    Args:
        decklist: Dictionary mapping card IDs to counts
        leader_id: Leader card ID
        unique_id: Unique identifier for the component elements
    
    Returns:
        A Div containing the export functionality
    """
    # Ensure leader is included in the decklist
    complete_decklist = ensure_leader_id(decklist, leader_id)
    export_str = decklist_to_export_str(complete_decklist)
    
    copy_btn_id = f"decklist-copy-btn-{unique_id}"
    export_id = f"decklist-export-{unique_id}"
    
    clipboard_script = f"""
    (function() {{
        function setupCopyButton_{unique_id.replace('-', '_')}() {{
            var copyBtn = document.getElementById('{copy_btn_id}');
            if (!copyBtn) return;
            
            // Remove any existing event listeners
            copyBtn.replaceWith(copyBtn.cloneNode(true));
            copyBtn = document.getElementById('{copy_btn_id}');
            
            copyBtn.addEventListener('click', function(e) {{
                e.preventDefault();
                e.stopPropagation();
                
                const decklistText = document.getElementById('{export_id}').textContent;
                
                if (navigator.clipboard && navigator.clipboard.writeText) {{
                    navigator.clipboard.writeText(decklistText).then(() => {{
                        const originalText = copyBtn.textContent;
                        copyBtn.textContent = 'Copied!';
                        copyBtn.disabled = true;
                        copyBtn.classList.add('bg-green-600');
                        copyBtn.classList.remove('bg-blue-600', 'hover:bg-blue-700');
                        
                        setTimeout(() => {{
                            copyBtn.textContent = originalText;
                            copyBtn.disabled = false;
                            copyBtn.classList.remove('bg-green-600');
                            copyBtn.classList.add('bg-blue-600', 'hover:bg-blue-700');
                        }}, 2000);
                    }}).catch(err => {{
                        console.error('Failed to copy: ', err);
                        // Fallback method
                        fallbackCopy_{unique_id.replace('-', '_')}(decklistText, copyBtn);
                    }});
                }} else {{
                    // Fallback for older browsers
                    fallbackCopy_{unique_id.replace('-', '_')}(decklistText, copyBtn);
                }}
            }});
        }}
        
        function fallbackCopy_{unique_id.replace('-', '_')}(text, button) {{
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            textArea.style.top = '-999999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            
            try {{
                document.execCommand('copy');
                const originalText = button.textContent;
                button.textContent = 'Copied!';
                button.disabled = true;
                button.classList.add('bg-green-600');
                button.classList.remove('bg-blue-600', 'hover:bg-blue-700');
                
                setTimeout(() => {{
                    button.textContent = originalText;
                    button.disabled = false;
                    button.classList.remove('bg-green-600');
                    button.classList.add('bg-blue-600', 'hover:bg-blue-700');
                }}, 2000);
            }} catch (err) {{
                console.error('Fallback copy failed: ', err);
            }}
            
            document.body.removeChild(textArea);
        }}
        
        // Setup immediately if DOM is ready
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', setupCopyButton_{unique_id.replace('-', '_')});
        }} else {{
            setupCopyButton_{unique_id.replace('-', '_')}();
        }}
        
        // Also setup after HTMX content loads
        document.addEventListener('htmx:afterSettle', function(evt) {{
            setTimeout(setupCopyButton_{unique_id.replace('-', '_')}, 100);
        }});
    }})();
    """
    
    return ft.Div(
        # Hidden export text area (not visible to user)
        ft.Pre(
            export_str,
            id=export_id,
            style="display: none;"  # Hide the text area
        ),
        
        # Copy button
        ft.Button(
            "Copy for Sim",
            id=copy_btn_id,
            cls="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded transition-colors w-full"
        ),
        
        # JavaScript for clipboard functionality 
        ft.Script(clipboard_script),
        
        cls="bg-gray-750 p-3 rounded-lg mb-4"
    ) 