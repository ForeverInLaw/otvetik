# Картинка Otvetik

- `otvetik-mascot.png` содержит исходник с прозрачным фоном.
- `otvetik-icon.webp` содержит версию 512×512 для Telegram-стикера, с сохранённой прозрачностью.
- README использует PNG. Иконка в приложении ещё не подключена.

SDK принимает `__icon__` в формате `StickerPackShortName/index`.
Для подключения своей картинки нужен опубликованный Telegram-стикер.
На проверенной сборке AyuGram индекс первого стикера равен нулю.

Источник: [метаданные Plugins SDK](https://plugins.exteragram.app/docs/plugin-class).

## Генерация

Создано встроенным инструментом `image_gen.imagegen`, с параметром `transparent_background=true`.
Референс внешности и стиля: `../pyosik/docs/pyosik-mascot.png` из соседнего проекта Pyosik.
WebP подготовлен уменьшением PNG, без изменения содержания картинки.

Промпт:

```text
Create a NEW raster mascot sticker for the Telegram plugin Otvetik, an assistant that suggests a written reply in its owner's style. The attached image is a reference for the dog's appearance, cutout quality and photographic sticker style only. Keep this same adorable scruffy sandy tan terrier with lively dark eyes, one ear upright and the other floppy. Make a distinct Otvetik variant: the dog happily holds a modern smartphone in its front paws, as if composing a message. Beside its head, a single simple mint-green speech bubble with three dark typing dots, large and clear. Chest-up close composition, dog and phone form one compact recognizable silhouette suitable for a tiny plugin icon. Realistic soft fur with a charming meme sticker expression, clean well-defined edges, soft studio light. Square 1024x1024 composition with a small transparent safety margin on every side and no cropping of ears. Actual transparent alpha background, no scenery or rectangular backing, no cast shadow. No microphone. No words, no letters, no app logos, no watermark. Focus on the dog's face and the reply bubble, avoid extra objects or small decorative details.
```
