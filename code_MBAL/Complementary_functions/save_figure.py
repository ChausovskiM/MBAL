import os
import time
from pathlib import Path


def save_figure(fig, path, attempts=3, **kwargs):
    """Атомарно сохраняет график и повторяет запись при временной блокировке файла."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(
        f'.{target.stem}.{os.getpid()}.tmp{target.suffix}'
    )

    try:
        for attempt in range(attempts):
            try:
                fig.savefig(temporary, **kwargs)
                os.replace(temporary, target)
                return
            except OSError:
                if attempt == attempts - 1:
                    raise
                time.sleep(0.1 * (attempt + 1))
    finally:
        temporary.unlink(missing_ok=True)
