# 字体与画布工具：读取系统字体（可变字重），创建 skia 画布并转成 numpy 数组
from functools import lru_cache

import numpy as np
import skia

FONT_FILES = {
    "serif": "C:/Windows/Fonts/NotoSerifSC-VF.ttf",
    "sans": "C:/Windows/Fonts/NotoSansSC-VF.ttf",
    "latin": "C:/Windows/Fonts/NotoSerif-Bold.ttf",
}
WGHT = 0x77676874  # 'wght' 轴


@lru_cache(maxsize=64)
def typeface(kind, weight=400):
    tf = skia.Typeface.MakeFromFile(FONT_FILES[kind])
    if kind in ("serif", "sans"):
        coord = skia.FontArguments.VariationPosition.Coordinate(WGHT, float(weight))
        args = skia.FontArguments()
        args.setVariationDesignPosition(skia.FontArguments.VariationPosition(
            skia.FontArguments.VariationPosition.Coordinates([coord])))
        tf = tf.makeClone(args)
    return tf


def font(kind, size, weight=400):
    f = skia.Font(typeface(kind, weight), size)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    f.setSubpixel(True)
    return f


def surface(w, h):
    info = skia.ImageInfo.Make(w, h, skia.ColorType.kRGBA_8888_ColorType, skia.AlphaType.kPremul_AlphaType)
    return skia.Surface.MakeRaster(info)


def to_array(surf):
    return np.array(surf.makeImageSnapshot().toarray(colorType=skia.ColorType.kRGBA_8888_ColorType,
                                                     alphaType=skia.AlphaType.kPremul_AlphaType))
