from services.storage.r2_storage import R2Storage


def get_media_storage(optional: bool = False) -> R2Storage | None:
    """返回配置好的媒体存储实例（当前：Cloudflare R2）。"""
    return R2Storage.from_env(optional=optional)
