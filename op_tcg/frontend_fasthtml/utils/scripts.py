from fasthtml import ft

def create_decklist_deep_link_script():
    """Create the JavaScript for deep-linking decklist modals - shared across pages."""
    return ft.Script("""
        (function(){
            function openDecklistFromURL(){
                try {
                    const params = new URLSearchParams(window.location.search);
                    const modal = params.get('modal');
                    if (modal !== 'decklist') return;
                    
                    const tid = params.get('tournament_id');
                    const pid = params.get('player_id');
                    const lid = params.get('lid');
                    
                    // Use unified endpoint for all cases
                    const endpoint = '/api/decklist-modal';
                    
                    // Build include object with all relevant parameters
                    const include = {};
                    if (lid) include.lid = lid;
                    if (tid) include.tournament_id = tid;
                    if (pid) include.player_id = pid;
                    
                    const metas = params.getAll('meta_format');
                    if (metas && metas.length) include.meta_format = metas;
                    
                    const region = params.get('region');
                    if (region) include.region = region;
                    
                    const currency = params.get('currency');
                    if (currency) include.currency = currency;
                    
                    // Tournament-specific parameters (handled by unified endpoint)
                    const days = params.get('days');
                    if (days) include.days = days;
                    
                    const placing = params.get('placing');
                    if (placing) include.placing = placing;
                    
                    // Require either lid OR (tid AND pid) for the unified endpoint
                    if (!lid && (!tid || !pid)) return;
                    
                    if (window.htmx && htmx.ajax) {
                        htmx.ajax('GET', endpoint, {target:'body',swap:'beforeend',values:include});
                    } else {
                        const qs = new URLSearchParams();
                        Object.entries(include).forEach(([k,v])=>{
                            if (Array.isArray(v)) v.forEach(val=>qs.append(k,val));
                            else if (v !== undefined && v !== '') qs.append(k,v);
                        });
                        fetch(endpoint + '?' + qs.toString()).then(r=>r.text()).then(html=>{
                            const container=document.createElement('div');
                            container.innerHTML=html; 
                            if (container.firstElementChild) document.body.appendChild(container.firstElementChild);
                        }).catch(()=>{});
                    }
                } catch(e) { /* noop */ }
            }
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', function(){ setTimeout(openDecklistFromURL, 50); });
            } else {
                setTimeout(openDecklistFromURL, 50);
            }
        })();
    """)