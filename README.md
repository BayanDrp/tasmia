# المسمّع الذكي

مدرب تلاوة القرآن الكريم برواية ورش عن نافع. يسجل المستخدم تلاوته، ثم يفرغ الصوت ويقارن بالنص المتوقع، ويعرض النتيجة كلمة كلمة.

يدعم وضعين:

* **تدقيق الحركات**: الوضع الافتراضي لكشف أخطاء التشكيل.
* **نموذج ورش**: وضع مخصص لتحسين التعرف على رواية ورش.

## التشغيل

```bash
export TASMIA_AI_URL=https://dr-pisto-tasmia-live.hf.space
make web-run
```

ثم افتح `http://localhost:8080`.

## تشغيل الذكاء الاصطناعي محليًا

يمكن تشغيل خدمة التفريغ على جهازك. تحتاج إلى Python 3.10 أو أحدث، و`ffmpeg`:

```bash
make ai-setup
make ai-run
```

`make ai-setup` يثبت الاعتماديات من `ai/requirements.txt`، ويستخدم نسخة CPU من PyTorch. قد يستغرق وقتًا عند أول تشغيل.

ثم شغّل الواجهة في طرفية أخرى دون ضبط `TASMIA_AI_URL`:

```bash
unset TASMIA_AI_URL
make web-run
```

افتراضيًا تحاول الخدمة Hugging Face Space أولًا ثم المحرك المحلي. لتشغيل المحرك المحلي فقط، اجعل `space_asr.enabled` مساويًا `false` في `config.json`.

## الاختبارات

```bash
make test
make web-test
```

## البنية

* `web/`: خدمة Go والواجهة الأمامية.
* `core/`: التحليل والتقييم.
* `ai/`: خدمة التفريغ المحلية الاختيارية.
* `space/`: تطبيق Hugging Face Space.
* `data/`: نص المصحف.
