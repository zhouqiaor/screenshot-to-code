#!/usr/bin/env python3
"""补齐 find_missing_classes.py 查出的 12 个缺失 artifact。

对应的运行时崩溃（逐个撞出来的顺序）：
  kotlin/jvm/internal/Intrinsics              -> kotlin-stdlib（已在 extra_jars 修）
  androidx/arch/core/internal/FastSafeIterableMap -> androidx.arch.core:core-common
  androidx/compose/ui/geometry/Offset         -> androidx.compose.ui:ui-geometry-android
  androidx/compose/material/ripple/RippleKt   -> androidx.compose.material:material-ripple-android
  ...
"""
import os, importlib.util, urllib.request, urllib.error, zipfile, io, time

ROOT = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("fetcher", os.path.join(ROOT, "fetch_compose_deps_v2.py"))
fetcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetcher)

MISSING = [
    ("androidx.arch.core", "core-common", "2.2.0"),                       # SafeIterableMap
    ("androidx.arch.core", "core-runtime", "2.2.0"),                      # ArchTaskExecutor
    ("androidx.compose.ui", "ui-geometry-android", "1.7.3"),              # Offset / CornerRadius
    ("androidx.compose.material", "material-ripple-android", "1.7.3"),    # RippleTheme
    ("androidx.concurrent", "concurrent-futures", "1.1.0"),               # ResolvableFuture
    ("androidx.customview", "customview-poolingcontainer", "1.0.0"),      # PoolingContainer
    ("androidx.emoji2", "emoji2", "1.3.0"),                               # EmojiCompat
    ("androidx.graphics", "graphics-path", "1.0.1"),                      # PathIterator
    ("androidx.interpolator", "interpolator", "1.0.0"),                   # FastOutLinearInInterpolator
    ("androidx.lifecycle", "lifecycle-viewmodel-savedstate", "2.8.4"),    # SavedStateHandle
    ("androidx.lifecycle", "lifecycle-runtime-compose-android", "2.8.4"), # LocalLifecycleOwnerKt
    ("androidx.versionedparcelable", "versionedparcelable", "1.1.1"),     # VersionedParcel
    # 第二轮扫描补的
    ("androidx.lifecycle", "lifecycle-livedata-core", "2.8.4"),           # MutableLiveData
    ("androidx.lifecycle", "lifecycle-process", "2.8.4"),                 # ProcessLifecycleInitializer
    ("com.google.guava", "listenablefuture", "1.0"),                      # ListenableFuture 单类桩
]

fetcher.ARTIFACTS = MISSING
fetcher.main()
