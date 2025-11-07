"""Cache manager for OpenReview API responses."""

import hashlib
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any

from loguru import logger


class CacheManager:
    """OpenReview APIレスポンスのキャッシュを管理."""
    
    def __init__(
        self,
        cache_dir: str = "storage/cache",
        ttl_hours: int = 24,
    ) -> None:
        """CacheManagerを初期化.
        
        Args:
        ----
            cache_dir: キャッシュディレクトリのパス
            ttl_hours: キャッシュの有効時間（時間単位）
        """
        self.cache_dir = Path(cache_dir)
        self.ttl_hours = ttl_hours
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _generate_cache_key(self, **kwargs: Any) -> str:
        """キャッシュキーを生成.
        
        Args:
        ----
            **kwargs: キーの生成に使用するパラメータ
            
        Returns:
        -------
            ハッシュ化されたキャッシュキー
        """
        # 辞書をソートして一貫性のある文字列を生成
        key_str = json.dumps(kwargs, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str, prefix: str = "") -> Path:
        """キャッシュファイルのパスを取得.
        
        Args:
        ----
            cache_key: キャッシュキー
            prefix: ファイル名のプレフィックス
            
        Returns:
        -------
            キャッシュファイルのパス
        """
        if prefix:
            filename = f"{prefix}_{cache_key}.json"
        else:
            filename = f"{cache_key}.json"
        return self.cache_dir / filename
    
    def _is_cache_valid(self, cache_path: Path) -> bool:
        """キャッシュが有効かチェック.
        
        Args:
        ----
            cache_path: キャッシュファイルのパス
            
        Returns:
        -------
            キャッシュが有効な場合True
        """
        if not cache_path.exists():
            return False
        
        # ファイルの更新時刻を取得
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        age = datetime.now() - mtime
        
        return age < timedelta(hours=self.ttl_hours)
    
    def get(self, prefix: str = "", **kwargs: Any) -> str | None:
        """キャッシュからデータを取得.
        
        Args:
        ----
            prefix: キャッシュファイルのプレフィックス
            **kwargs: キャッシュキーの生成に使用するパラメータ
            
        Returns:
        -------
            キャッシュされたデータ（JSON文字列）、存在しない場合はNone
        """
        cache_key = self._generate_cache_key(**kwargs)
        cache_path = self._get_cache_path(cache_key, prefix)
        
        if self._is_cache_valid(cache_path):
            logger.debug(f"Cache hit: {cache_path.name}")
            return cache_path.read_text(encoding="utf-8")
        
        logger.debug(f"Cache miss: {cache_path.name}")
        return None
    
    def set(self, data: str, prefix: str = "", **kwargs: Any) -> None:
        """データをキャッシュに保存.
        
        Args:
        ----
            data: 保存するデータ（JSON文字列）
            prefix: キャッシュファイルのプレフィックス
            **kwargs: キャッシュキーの生成に使用するパラメータ
        """
        cache_key = self._generate_cache_key(**kwargs)
        cache_path = self._get_cache_path(cache_key, prefix)
        
        cache_path.write_text(data, encoding="utf-8")
        logger.debug(f"Cache saved: {cache_path.name}")
    
    def clear(self, prefix: str = "") -> int:
        """キャッシュをクリア.
        
        Args:
        ----
            prefix: 削除するキャッシュファイルのプレフィックス（指定しない場合は全て削除）
            
        Returns:
        -------
            削除したファイル数
        """
        if prefix:
            pattern = f"{prefix}_*.json"
        else:
            pattern = "*.json"
        
        deleted = 0
        for cache_file in self.cache_dir.glob(pattern):
            cache_file.unlink()
            deleted += 1
        
        logger.info(f"Cleared {deleted} cache file(s)")
        return deleted
    
    def get_cache_info(self) -> dict[str, Any]:
        """キャッシュ情報を取得.
        
        Returns:
        -------
            キャッシュ情報の辞書
        """
        cache_files = list(self.cache_dir.glob("*.json"))
        valid_files = [f for f in cache_files if self._is_cache_valid(f)]
        
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            "total_files": len(cache_files),
            "valid_files": len(valid_files),
            "expired_files": len(cache_files) - len(valid_files),
            "total_size_mb": total_size / (1024 * 1024),
            "cache_dir": str(self.cache_dir),
            "ttl_hours": self.ttl_hours,
        }

