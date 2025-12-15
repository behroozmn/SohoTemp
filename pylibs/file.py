class FileManager:

    @classmethod
    def read_strip(cls, path: str, default: str = "") -> str:
        """خواندن یک فایل متنی و إستریپ(حذف ابتدا و انتها) آن
            Args:
                path (str): مسیر فایل.
                default (str|None): مقدار بازگشتی در صورت خطا.

            Returns: str: محتوای فایل یا مقدار پیش‌فرض.
            """
        try:
            with open(path, 'r') as f:
                return f.read().strip()
        except (OSError, IOError):
            return default
