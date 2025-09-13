// Reusable Donut (Doughnut) chart renderer using Chart.js v4
// Keeps logic separated for reuse across pages

(function(){
  window.renderDonutChart = function(containerId, labels, values, colors, images){
    try {
      const canvas = document.getElementById(containerId);
      if (!canvas || !window.Chart) return;
      
      // Destroy existing chart more thoroughly
      const existing = window.Chart.getChart ? window.Chart.getChart(containerId) : null;
      if (existing) {
        existing.destroy();
      }
      
      // Clear canvas completely
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      // Reset canvas size to container
      const container = canvas.parentElement;
      if (container) {
        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight;
      }
      
      const total = (Array.isArray(values) ? values : []).reduce((a,b)=>a+(+b||0),0) || 1;
      const data = {
        labels: labels,
        datasets: [{
          data: values,
          backgroundColor: colors,
          borderColor: colors.map(c=>c),
          borderWidth: 1
        }]
      };
      const options = {
        responsive: true,
        maintainAspectRatio: false,
        layout: {
          padding: 20  // Add padding to ensure chart fits fully
        },
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            enabled: false  // Disable default tooltip, use custom one
          }
        },
        hover: {
          mode: 'nearest',
          intersect: true
        },
        events: ['mousemove', 'mouseout', 'click', 'touchstart', 'touchmove'],
        onHover: function(event, chartElements) {
          const tooltipEl = document.getElementById('chartjs-tooltip');
          
          if (!tooltipEl) {
            const div = document.createElement('div');
            div.id = 'chartjs-tooltip';
            document.body.appendChild(div);
          }
          
          if (!chartElements || chartElements.length === 0) {
            tooltipEl.style.opacity = 0;
            return;
          }
          
          const element = chartElements[0];
          const dataIndex = element.index;
          const label = labels[dataIndex];
          const value = values[dataIndex];
          const image = images && images[dataIndex] ? images[dataIndex] : '';
          const pct = ((value/total)*100).toFixed(1);
          
          // Create tooltip content with flex layout similar to bubble chart
          const tooltipContent = `
            <div style="
              display: flex;
              gap: 16px;
              min-width: 300px;
              height: 120px;
              padding: 0;
            ">
              <div style="
                flex: 0 0 30%;
                height: 100%;
                display: flex;
                align-items: center;
                justify-content: center;
                overflow: hidden;
                padding: 0;
                margin: 0;
              ">
                ${image ? `<img src="${image}" style="width: 100%; height: 100%; object-fit: contain; display: block;">` : ''}
              </div>
              <div style="
                flex: 0 0 70%;
                padding: 12px 16px 12px 0;
                display: flex;
                flex-direction: column;
                justify-content: center;
              ">
                <div style="font-weight: bold; margin-bottom: 12px; font-size: 1.2em; white-space: normal;">${label}</div>
                <div style="margin: 4px 0;">Count: ${value}</div>
                <div style="margin: 4px 0;">Percentage: ${pct}%</div>
              </div>
            </div>
          `;
          
          tooltipEl.innerHTML = tooltipContent;
          tooltipEl.style.opacity = 1;
          tooltipEl.style.position = 'absolute';
          tooltipEl.style.backgroundColor = 'rgba(17, 24, 39, 0.95)';
          tooltipEl.style.color = '#ffffff';
          tooltipEl.style.borderRadius = '4px';
          tooltipEl.style.border = '1px solid #374151';
          tooltipEl.style.pointerEvents = 'none';
          tooltipEl.style.zIndex = 9999;
          tooltipEl.style.transform = 'translate(-50%, -100%)';
          tooltipEl.style.transition = 'all .1s ease';
          tooltipEl.style.padding = '0';
          tooltipEl.style.overflow = 'hidden';
          
          // Position the tooltip
          const canvasPosition = canvas.getBoundingClientRect();
          const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
          const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
          
          tooltipEl.style.left = (canvasPosition.left + scrollLeft + event.x) + 'px';
          tooltipEl.style.top = (canvasPosition.top + scrollTop + event.y - 10) + 'px';
        },
        cutout: '50%',  // Slightly smaller cutout for better visibility
        animation: {
          duration: 300  // Faster animation for HTMX updates
        }
      };
      
      // Small delay to ensure DOM is ready
      setTimeout(() => {
        new Chart(ctx, { type: 'doughnut', data, options });
      }, 50);
      
    } catch(e) { console.error('renderDonutChart failed', e); }
  }

  // Cleanup any existing charts on HTMX swaps targeting containers with canvases
  document.addEventListener('htmx:beforeSwap', function(event){
    try {
      if (!window.Chart) return;
      const target = event.target || event.detail && event.detail.target;
      const root = target || document;
      const canvases = root.querySelectorAll && root.querySelectorAll('canvas[id]');
      if (!canvases) return;
      canvases.forEach(cv => {
        const id = cv.getAttribute('id');
        if (!id) return;
        const chart = window.Chart.getChart ? window.Chart.getChart(id) : null;
        if (chart) chart.destroy();
      });
      const tooltip = document.getElementById('chartjs-tooltip');
      if (tooltip) tooltip.remove();
    } catch(e) { /* noop */ }
  });
})();


