from typing import List

try:
    import GPUtil
except ImportError:  # pragma: no cover
    GPUtil = None


def get_gpu_info_html() -> str:
    """Return HTML-formatted GPU information for display in the UI."""
    if GPUtil is None:
        return "<b>GPU Info:</b> <i>GPUtil not installed.</i>"

    try:
        gpus: List["GPUtil.GPU"] = GPUtil.getGPUs()
        if not gpus:
            return "<b>GPU Info:</b> <i>No GPU detected.</i>"

        lines: List[str] = ["<b>GPU Info:</b>"]
        for gpu in gpus:
            lines.append(
                f"<b>GPU {gpu.id}:</b> {gpu.name}<br>"
                f"&nbsp;&nbsp;Load: {gpu.load*100:.1f}%<br>"
                f"&nbsp;&nbsp;Memory: {gpu.memoryUsed:.1f}MB / {gpu.memoryTotal:.1f}MB ({gpu.memoryUtil*100:.1f}%)<br>"
                f"&nbsp;&nbsp;Temperature: {gpu.temperature}°C<br>"
            )
        return "<div style='line-height:1.5;'>" + "".join(lines) + "</div>"
    except Exception as exc:
        return f"<b>GPU Info:</b> <span style='color:#b00;'><i>Error: {exc}</i></span>" 