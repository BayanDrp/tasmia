---
title: Tasmia Live
emoji: 📖
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: 6.31.0
python_version: 3.11
app_file: app.py
pinned: false
---

# Tasmia Live

واجهة تجريبية لتفريغ التلاوة القرآنية وتحليلها. ارفع تسجيلًا أو استخدم الميكروفون،
ثم اعرض التفريغ، أو استخدم واجهة الـ API لعرض النص المتوقع وكشف الأخطاء.

يستخدم التطبيق نموذج
`rabah2026/wav2vec2-large-xlsr-53-arabic-quran-v_final`، وهو نموذج Wav2Vec2
مدرّب على بيانات تلاوات قرآنية. بطاقة النموذج لا تؤكد أنه مخصص لرواية ورش،
لذلك يجب التحقق من مخرجاته على تسجيلات ورش موثوقة.

يدعم التسجيلات حتى 3 دقائق. النموذج يعمل على CPU أو GPU؛ وقد يستغرق تحميله
وقتًا في أول استخدام. التفريغ آلي وقد يخطئ في الكلمات أو التشكيل؛ راجعه على
مصحف موثوق.

## بنية الملفات

- `app.py`: واجهة الـ API (gradio.Server) وواجهة العرض
- `judge.py`: محاذاة النص وتقييم التلاوة
- `engine.py`: منطق النماذج والتفريغ
- `config.py`: إعدادات مشتركة
- `tasmia_core/`: نسخة مُورَّدة من حزمة `core/tasmia_core` في المستودع الرئيسي
  (التفريغ والمحاذاة والتقييم)؛ عند تعديل النواة أعِد مزامنتها إلى هنا.
- `data/quran/quran.json`: نص المصحف الذي يستخدمه المحلل.

## API

`POST /api/transcribe` يستقبل `multipart/form-data`:

- `audio`: الملف الصوتي.
- `model`: `quick` أو `warsh` أو مُعرِّف نموذج على Hugging Face.
- `surah`, `ayah_from`, `ayah_to`, `mode`: اختيارية. عند إرسال `surah`
  يعيد الخادم النص ونتيجة التحليل الكاملة (الكلمات، الأخطاء، والدرجة).
- `mode`: `standard` أو `warsh` أو `remove_tashkeel`.
