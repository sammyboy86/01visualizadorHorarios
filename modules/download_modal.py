# -*- coding: utf-8 -*-
"""
Modal y notificaciones de descarga interactiva con GIF animado.
"""
import base64
import math
import os
import streamlit as st

# Compatibilidad con st.dialog (Streamlit >= 1.34) o st.experimental_dialog
if hasattr(st, "dialog"):
    _dialog_decorator = st.dialog
elif hasattr(st, "experimental_dialog"):
    _dialog_decorator = st.experimental_dialog
else:
    _dialog_decorator = None


def _generate_download_gif_bytes() -> bytes:
    """Genera un archivo GIF89a animado (12 fotogramas) de un spinner / flecha de descarga."""
    w, h = 64, 64
    num_frames = 12

    # Paleta de 8 colores (RGB)
    palette = [
        (26, 29, 41),    # 0: Fondo oscuro (#1a1d29)
        (37, 42, 59),    # 1: Pista del anillo (#252a3b)
        (79, 139, 249),  # 2: Azul primario (#4f8bf9)
        (108, 99, 255),  # 3: Violeta acento (#6c63ff)
        (96, 165, 250),  # 4: Azul claro (#60a5fa)
        (147, 197, 253), # 5: Brillo (#93c5fd)
        (250, 250, 250), # 6: Blanco (#fafafa)
        (16, 185, 129),  # 7: Verde esmeralda (#10b981)
    ]
    while len(palette) < 256:
        palette.append((0, 0, 0))

    color_table = bytearray()
    for r, g, b in palette:
        color_table.extend([r, g, b])

    # Compresor LZW estándar para GIF
    def lzw_compress(pixels: list[int], min_code_size: int = 8) -> bytes:
        clear_code = 1 << min_code_size
        end_of_info = clear_code + 1
        cur_code_size = min_code_size + 1
        next_code = end_of_info + 1
        max_code = 1 << cur_code_size
        code_table = {bytes([i]): i for i in range(clear_code)}

        bits_buffer = 0
        bits_count = 0
        output_bytes = bytearray()

        def emit(c):
            nonlocal bits_buffer, bits_count, output_bytes
            bits_buffer |= (c << bits_count)
            bits_count += cur_code_size
            while bits_count >= 8:
                output_bytes.append(bits_buffer & 0xFF)
                bits_buffer >>= 8
                bits_count -= 8

        emit(clear_code)
        prefix = b""
        for idx in pixels:
            c = bytes([idx])
            pc = prefix + c
            if pc in code_table:
                prefix = pc
            else:
                emit(code_table[prefix])
                if next_code < 4096:
                    code_table[pc] = next_code
                    next_code += 1
                    if next_code > max_code and cur_code_size < 12:
                        cur_code_size += 1
                        max_code = 1 << cur_code_size
                else:
                    emit(clear_code)
                    code_table = {bytes([i]): i for i in range(clear_code)}
                    cur_code_size = min_code_size + 1
                    next_code = end_of_info + 1
                    max_code = 1 << cur_code_size
                prefix = c
        if prefix:
            emit(code_table[prefix])
        emit(end_of_info)
        if bits_count > 0:
            output_bytes.append(bits_buffer & 0xFF)

        # Empaquetar en sub-bloques de longitud <= 255
        result = bytearray([min_code_size])
        i = 0
        while i < len(output_bytes):
            chunk = output_bytes[i:i + 255]
            result.append(len(chunk))
            result.extend(chunk)
            i += len(chunk)
        result.append(0)
        return bytes(result)

    # Construir cabecera GIF89a
    gif = bytearray()
    gif.extend(b"GIF89a")
    gif.extend(w.to_bytes(2, "little"))
    gif.extend(h.to_bytes(2, "little"))
    gif.append(0xF7)  # GCT presente, 8 bits/pixel, 256 colores
    gif.append(0)     # Color de fondo: índice 0
    gif.append(0)     # Aspect ratio
    gif.extend(color_table)

    # Extensión de la aplicación Netscape 2.0 (bucle infinito)
    gif.extend(b"\x21\xFF\x0BNETSCAPE2.0\x03\x01\x00\x00\x00")

    # Generar fotogramas
    for t in range(num_frames):
        # Graphic Control Extension (Demora: 8 = 80ms)
        gif.extend(b"\x21\xF9\x04\x08\x08\x00\x00\x00")

        # Image Descriptor
        gif.append(0x2C)
        gif.extend((0).to_bytes(2, "little"))
        gif.extend((0).to_bytes(2, "little"))
        gif.extend(w.to_bytes(2, "little"))
        gif.extend(h.to_bytes(2, "little"))
        gif.append(0)

        # Dibujar píxeles del fotograma
        frame_pixels = [0] * (w * h)
        angle_head = (t / num_frames) * 2 * math.pi
        bounce_y = int(2.5 * math.sin((t / num_frames) * 2 * math.pi))

        # 1. Anillo exterior con arco giratorio
        for y in range(h):
            dy = y - 31.5
            for x in range(w):
                dx = x - 31.5
                r = math.sqrt(dx * dx + dy * dy)
                if 25.0 <= r <= 29.5:
                    theta = math.atan2(dy, dx)
                    diff = (theta - angle_head) % (2 * math.pi)
                    if diff < math.pi * 0.75:
                        if diff < math.pi * 0.2:
                            frame_pixels[y * w + x] = 6  # Blanco
                        elif diff < math.pi * 0.45:
                            frame_pixels[y * w + x] = 5  # Azul claro
                        else:
                            frame_pixels[y * w + x] = 4  # Azul medio
                    elif 26.5 <= r <= 28.0:
                        frame_pixels[y * w + x] = 1

        # 2. Flecha de descarga que rebota suavemente
        stem_top = 18 + bounce_y
        stem_bottom = 32 + bounce_y

        for y in range(stem_top, stem_bottom):
            if 0 <= y < h:
                frame_pixels[y * w + 30] = 2
                frame_pixels[y * w + 31] = 6
                frame_pixels[y * w + 32] = 2

        tip_y = 38 + bounce_y
        for i_head in range(7):
            y_head = stem_bottom - 2 + i_head
            if 0 <= y_head < h:
                for x_head in range(31 - (6 - i_head), 32 + (6 - i_head) + 1):
                    if 0 <= x_head < w:
                        frame_pixels[y_head * w + x_head] = 4 if i_head > 3 else 2

        # 3. Bandeja receptora inferior
        tray_y = 46
        for x_tray in range(21, 43):
            if 0 <= tray_y < h:
                frame_pixels[tray_y * w + x_tray] = 3
                frame_pixels[(tray_y + 1) * w + x_tray] = 3

        for y_tray in range(41, tray_y + 2):
            if 0 <= y_tray < h:
                frame_pixels[y_tray * w + 21] = 3
                frame_pixels[y_tray * w + 22] = 3
                frame_pixels[y_tray * w + 41] = 3
                frame_pixels[y_tray * w + 42] = 3

        gif.extend(lzw_compress(frame_pixels, 8))

    gif.append(0x3B)
    return bytes(gif)


# Inicializar o cargar el GIF animado
_MODULES_DIR = os.path.dirname(os.path.abspath(__file__))
_GIF_FILE = os.path.join(_MODULES_DIR, "downloading.gif")

if not os.path.exists(_GIF_FILE):
    try:
        _gif_bytes = _generate_download_gif_bytes()
        with open(_GIF_FILE, "wb") as _f:
            _f.write(_gif_bytes)
    except Exception:
        _gif_bytes = b""
else:
    with open(_GIF_FILE, "rb") as _f:
        _gif_bytes = _f.read()

_GIF_B64 = base64.b64encode(_gif_bytes).decode() if _gif_bytes else ""


def render_dialog_content(filename: str, file_path_or_blob):
    """Contenido visual del modal de descarga con GIF animado."""
    size_mb = 0.0
    if isinstance(file_path_or_blob, str) and os.path.exists(file_path_or_blob):
        size_mb = os.path.getsize(file_path_or_blob) / (1024 * 1024)
    elif isinstance(file_path_or_blob, (bytes, bytearray)):
        size_mb = len(file_path_or_blob) / (1024 * 1024)

    # Si el GIF está disponible en base64 se muestra la animación, si no, el emoji como fallback
    gif_html = (
        f'<img src="data:image/gif;base64,{_GIF_B64}" alt="Descargando..." style="width:60px; height:60px; display:block; margin:auto;" />'
        if _GIF_B64
        else '<span style="font-size: 2.3rem;">📥</span>'
    )

    st.markdown(
        f"""
        <div style="text-align: center; padding: 0.5rem 0 1rem 0;">
            <div style="width: 76px; height: 76px; margin: 0 auto 1.2rem auto; border-radius: 50%;
                        background: linear-gradient(135deg, rgba(79,139,249,0.15), rgba(108,99,255,0.22));
                        border: 2px solid rgba(79,139,249,0.38); display: flex; align-items: center;
                        justify-content: center; box-shadow: 0 0 24px rgba(79,139,249,0.3); overflow: hidden;">
                {gif_html}
            </div>
            <h3 style="margin: 0 0 0.5rem 0; color: #fafafa; font-family: 'Outfit', sans-serif;">
                ¡Descarga en proceso!
            </h3>
            <div style="display: inline-block; background: rgba(79,139,249,0.12);
                        border: 1px solid rgba(79,139,249,0.3); border-radius: 8px;
                        padding: 0.35rem 0.9rem; color: #60a5fa; font-weight: 600;
                        font-family: monospace; font-size: 0.95rem; margin-bottom: 1rem;">
                {filename} &middot; {size_mb:.1f} MB
            </div>
            <p style="color: #94a3b8; font-size: 0.92rem; line-height: 1.5; margin-bottom: 1.2rem;">
                Tu solicitud está siendo procesada. El archivo se está transfiriendo a tu equipo
                y se guardará en tu carpeta de descargas habitual.
            </p>
            <div style="background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.3);
                        border-radius: 10px; padding: 0.6rem 1rem; color: #a7f3d0;
                        font-size: 0.88rem; font-weight: 500; display: flex; align-items: center;
                        justify-content: center; gap: 0.5rem; margin-bottom: 1.4rem;">
                <span>✔</span> Solicitud enviada correctamente al navegador
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        if isinstance(file_path_or_blob, str) and os.path.exists(file_path_or_blob):
            with open(file_path_or_blob, "rb") as fp:
                data_to_dl = fp.read()
        else:
            data_to_dl = file_path_or_blob

        st.download_button(
            "⬇️ Descargar de nuevo",
            data=data_to_dl,
            file_name=filename,
            mime="application/zip",
            key=f"modal_redownload_{filename}",
            use_container_width=True,
            help="Haz clic si tu navegador bloqueó la descarga automática",
        )
    with c2:
        if st.button("Cerrar", key=f"modal_close_{filename}", use_container_width=True, type="primary"):
            st.rerun()


if _dialog_decorator:
    @_dialog_decorator("📥 Descarga en proceso")
    def _modal_dialog(filename: str, file_path_or_blob):
        render_dialog_content(filename, file_path_or_blob)


def show_download_dialog(filename: str, file_path_or_blob):
    """Muestra el modal de descarga interactivo y un toast de confirmación."""
    try:
        st.toast(f"📥 Descarga iniciada: {filename}", icon="📥")
    except Exception:
        pass

    if _dialog_decorator:
        _modal_dialog(filename, file_path_or_blob)
    else:
        st.info(f"📥 Descargando **{filename}**...")
        render_dialog_content(filename, file_path_or_blob)
