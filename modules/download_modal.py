# -*- coding: utf-8 -*-
"""
Modal y controlador de descargas interactivo.
"""
import streamlit.components.v1 as components


def inject_download_modal():
    """Inyecta el modal interactivo de descarga y el interceptor en el cliente."""
    modal_js = r"""
    <script id="utc-download-modal-script">
    (function() {
        const win = window.parent || window;
        const doc = win.document || document;

        try {
            const frame = window.frameElement;
            if (frame) {
                frame.style.display = 'none';
                frame.style.height = '0px';
                frame.style.border = 'none';
                frame.style.margin = '0px';
                frame.style.padding = '0px';
            }
        } catch (e) {}

        // Asegurar que el overlay del modal exista en el body principal
        if (!doc.getElementById('utc-download-modal-overlay')) {
            const overlay = doc.createElement('div');
            overlay.id = 'utc-download-modal-overlay';
            overlay.className = 'utc-modal-overlay';
            overlay.innerHTML = `
                <div class="utc-modal-card">
                    <button class="utc-modal-close" id="utc-modal-close-btn" title="Cerrar" aria-label="Cerrar">&times;</button>
                    <div class="utc-modal-icon-wrap">
                        <div class="utc-icon-circle pulsing" id="utc-icon-circle">
                            <svg class="utc-icon-download" id="utc-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                                <path class="arrow-stem" d="M12 3v13"></path>
                                <polyline class="arrow-head" points="7 11 12 16 17 11"></polyline>
                                <path class="tray-line" d="M4 20h16"></path>
                            </svg>
                        </div>
                    </div>
                    <h3 class="utc-modal-title" id="utc-modal-title">Descargando archivo...</h3>
                    <div class="utc-modal-filename" id="utc-modal-filename">archivo.zip</div>
                    <p class="utc-modal-desc" id="utc-modal-desc">
                        Su solicitud se está procesando. El archivo se descargará en su equipo.
                    </p>
                    <div class="utc-progress-track">
                        <div class="utc-progress-bar" id="utc-progress-bar"></div>
                    </div>
                    <div class="utc-status-badge" id="utc-status-badge">
                        <span class="utc-status-dot"></span>
                        <span id="utc-status-text">Procesando descarga...</span>
                    </div>
                </div>
            `;
            doc.body.appendChild(overlay);

            const closeBtn = doc.getElementById('utc-modal-close-btn');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    overlay.classList.remove('active');
                });
            }

            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    overlay.classList.remove('active');
                }
            });
        }

        // Evitar registrar listeners duplicados
        if (win.__utcDownloadModalHandlerAttached) return;
        win.__utcDownloadModalHandlerAttached = true;

        function showModal(filename) {
            const overlay = doc.getElementById('utc-download-modal-overlay');
            if (!overlay) return;

            const titleEl = doc.getElementById('utc-modal-title');
            const fileEl = doc.getElementById('utc-modal-filename');
            const descEl = doc.getElementById('utc-modal-desc');
            const statusEl = doc.getElementById('utc-status-text');
            const circle = doc.getElementById('utc-icon-circle');
            const bar = doc.getElementById('utc-progress-bar');
            const badge = doc.getElementById('utc-status-badge');

            if (titleEl) titleEl.textContent = 'Descargando archivo...';
            if (fileEl) fileEl.textContent = filename;
            if (descEl) descEl.textContent = 'Su solicitud se está procesando. El archivo se descargará en su equipo.';
            if (statusEl) statusEl.textContent = 'Descargando archivo...';

            if (circle) {
                circle.className = 'utc-icon-circle pulsing';
                circle.innerHTML = `
                    <svg class="utc-icon-download" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <path class="arrow-stem" d="M12 3v13"></path>
                        <polyline class="arrow-head" points="7 11 12 16 17 11"></polyline>
                        <path class="tray-line" d="M4 20h16"></path>
                    </svg>
                `;
            }

            if (bar) bar.className = 'utc-progress-bar';
            if (badge) badge.className = 'utc-status-badge';

            overlay.classList.add('active');
        }

        function setComplete(filename) {
            const overlay = doc.getElementById('utc-download-modal-overlay');
            const titleEl = doc.getElementById('utc-modal-title');
            const descEl = doc.getElementById('utc-modal-desc');
            const statusEl = doc.getElementById('utc-status-text');
            const circle = doc.getElementById('utc-icon-circle');
            const bar = doc.getElementById('utc-progress-bar');
            const badge = doc.getElementById('utc-status-badge');

            if (circle) {
                circle.className = 'utc-icon-circle completed';
                circle.innerHTML = `
                    <svg class="utc-icon-download" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="20 6 9 17 4 12"></polyline>
                    </svg>
                `;
            }

            if (titleEl) titleEl.textContent = '✅ ¡Descarga completada!';
            if (descEl) descEl.textContent = 'El archivo se ha transferido exitosamente.';
            if (statusEl) statusEl.textContent = 'Descarga finalizada';

            if (bar) bar.classList.add('completed');
            if (badge) badge.classList.add('completed');

            setTimeout(() => {
                if (overlay) overlay.classList.remove('active');
            }, 1400);
        }

        // Interceptar clics en botones de descarga de Streamlit
        doc.addEventListener('click', async function(e) {
            const btn = e.target.closest('div[data-testid="stDownloadButton"] a, a[download]');
            if (!btn) return;

            if (btn.classList.contains('utc-handled')) return;
            if (btn.__isDownloading) return;

            const href = btn.href || btn.getAttribute('href');
            if (!href) return;

            const filename = btn.getAttribute('download') || btn.innerText.replace(/^[⬇️\s]+/, '').trim() || 'descarga.zip';

            e.preventDefault();
            e.stopPropagation();

            btn.__isDownloading = true;
            btn.classList.add('utc-btn-downloading');
            showModal(filename);

            try {
                const response = await win.fetch(href);
                if (!response.ok) throw new Error('Fetch failed with status ' + response.status);
                const blob = await response.blob();

                const blobUrl = win.URL.createObjectURL(blob);
                const tempLink = doc.createElement('a');
                tempLink.href = blobUrl;
                tempLink.download = filename;
                tempLink.className = 'utc-handled';
                doc.body.appendChild(tempLink);
                tempLink.click();
                doc.body.removeChild(tempLink);
                setTimeout(() => win.URL.revokeObjectURL(blobUrl), 20000);

                setComplete(filename);
            } catch (err) {
                console.warn('Direct fetch failed, falling back to browser download:', err);
                const fallbackLink = doc.createElement('a');
                fallbackLink.href = href;
                fallbackLink.download = filename;
                fallbackLink.className = 'utc-handled';
                doc.body.appendChild(fallbackLink);
                fallbackLink.click();
                doc.body.removeChild(fallbackLink);

                setTimeout(() => {
                    setComplete(filename);
                }, 1000);
            } finally {
                setTimeout(() => {
                    btn.__isDownloading = false;
                    btn.classList.remove('utc-btn-downloading');
                }, 1600);
            }
        }, true);
    })();
    </script>
    """
    components.html(modal_js, height=0)
