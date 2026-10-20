# Картинка Otvetik

- `otvetik-mascot.png` содержит исходник с прозрачным фоном.
- `otvetik-icon.webp` содержит версию 512×512 для Telegram-стикера, с сохранённой прозрачностью.
- README использует PNG. Иконка в приложении подключена через `__icon__ = "OtvetikPlugin/0"`.

SDK принимает `__icon__` в формате `StickerPackShortName/index`.
Картинка опубликована в [стикерпаке Otvetik](https://t.me/addstickers/OtvetikPlugin),
которым владеет [@nevermorelove](https://t.me/nevermorelove).
На проверенной сборке AyuGram индекс первого стикера равен нулю.

Источник: [метаданные Plugins SDK](https://plugins.exteragram.app/docs/plugin-class).

## Генерация

Создано встроенным инструментом `image_gen.imagegen`, с параметром `transparent_background=true`.
Персонаж Otvetik: попугай-корелла с голубым пузырём ответа. Картинка создана с нуля, без изображения-референса.
WebP подготовлен уменьшением PNG, без изменения содержания картинки.

Промпт:

```text
Use case: stylized-concept. Asset type: a brand-new mascot sticker and tiny Telegram plugin icon for Otvetik, a tool that suggests a reply in its owner's writing style. Create one charming expressive cockatiel parrot with soft slate-grey feathers, a bright pale-yellow face, orange cheek patches, a lifted crest and an alert cheeky expression, head tilted slightly as if about to speak. Close head-and-chest portrait in a compact centered silhouette. A single glossy sky-blue speech bubble with three dark typing dots sits close beside the bird's beak; make the bubble and bird face both readable at 64px. Warm realistic feather detail with a playful premium photographic meme-sticker feel, soft studio light. Visually distinct character with no reference image. Square composition, keep the entire crest and bubble inside frame with a clear transparent safety margin. Real transparent alpha background, no scenery, no rectangular backing, no shadow under the character. No dog, no mammal, no phone, no microphone, no keyboard, no clothing, no text, no letters, no logo, no watermark, no extra decorative objects. One clean finished sticker, not a grid or mockup.
```
