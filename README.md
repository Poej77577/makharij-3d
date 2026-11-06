# مخارج — تنفيذ الخطة الهندسية

الطلب المعتمد في [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md).
الحالة الحالية في [docs/WORKING_STATE.md](docs/WORKING_STATE.md).

**M0 مكتملة تقنيًا، وM1 ما زالت قيد استكمال الأصول الداخلية.** يوجد أساس رأس
خارجي مرشح فعلي وقابل للتحرير، وليس نموذج مخارج مكتملًا أو معتمدًا. التطبيق
الحالي يحافظ على العارض التقني القديم وتجربة الراء. الرأس الجديد دراسة مصدر
مستقلة إلى أن يكتمل التجميع التشريحي.

## التشغيل والتحقق

الإصدارات المختبرة: Node 24.19.0، npm 11.9.0، Blender 4.3.2، وPython 3.12
لفحص الهندسة. Python المضمن في Blender منفصل عن حزم الفحص الأصلية.

```sh
npm ci --no-audit --no-fund
python -m venv --system-site-packages .venv-qa
.venv-qa/bin/python -m pip install -r scripts/qa/requirements.txt
npm run build
npm run test:unit
python tools/qa/verify_sources.py
npm run preview -- --port 4173 --strictPort
```

في طرفية ثانية، مع Chromium مثبت في المسار المختبر:

```sh
npm run test:e2e
```

هذا فحص فعلي لتحميل النموذج المحفوظ وتغير الصورة وعودة الوضع وعدم وجود أخطاء
JavaScript، وليس إثبات اجتياز التشريح الجديد. اختبارات عقود البيانات تستخدم
fixtures صناعية معلنة ولا تمثل نموذجًا أو اعتمادًا علميًا.

## دراسة الرأس الجديد

الأصل الكامل وحقوقه وبصماته في `assets/source/makehuman`. القاعدة والعيون
واستهدافات الوجه مرخصة CC0 صراحة؛ لم تُنسخ شيفرة تطبيق MakeHuman إلى المنتج.
تظل مصادر Badin/ArtiSynth البحثية محفوظة بإشعاراتها، مع بيان حدود التسجيل.

```sh
blender --background --threads 2 --python tools/blender/candidate_study.py -- --candidate makehuman --adult --export-study --resolution 640 --samples 48
.venv-qa/bin/python tools/qa/verify_head_study.py
```

المخرجات في `artifacts/milestone-evidence/M1/makehuman-adult-head-study/rest`:
ملف Blender قابل للتحرير، وGLB فعلي، وصور من ثلاث زوايا، وبصمات ومقارنة مستقلة
بين هندسة المصدر والملف المصدّر. ملف الدراسة يستخدم محاور موثقة بالمتر؛
لا يحتوي تجميع الفم والأنف والحلق الكامل أو تجهيز نطق معتمدًا.

القرار وحدود المرشحين وخطة الاستكمال في
[docs/ASSET_DECISION.md](docs/ASSET_DECISION.md) و[docs/ANATOMY_SPEC.md](docs/ANATOMY_SPEC.md).

## الأوامر المتاحة

- `npm run typecheck`: فحص TypeScript.
- `npm run assets:inspect -- --input PATH --out PATH`: قراءة وقياس ملفات
  Blender/OBJ/glTF الفعلية، دون تعديل المدخل.
- `npm run package:source`: حزمة مصدر مع فحص CRC وبصمات جميع الملفات، خارج
  المستودع في `/workspace/artifacts/makharij-source.zip`.

أوامر قبول التشريح الكامل وتصدير نموذج الإنتاج وفحص حركاته ستُربط عند بلوغ
مراحلها. لا توجد سكربتات نجاح وهمية لهذه الأعمال غير المنفذة.

## الحفظ والعائق الحالي

فرع التطوير `codex/anatomy-foundation-v2` رُفع إلى GitHub، واختُبر استرجاع
نسخة مستقلة منه ومطابقة الملفات. لم يحدث دمج في الفرع الرئيسي أو نشر موقع.

تنزيل الحزمة الرسمية للأسنان واللسان المتوافقين متوقف على السماح بالنطاق
`files2.makehumancommunity.org`. أضيف النطاق إلى مسودة إعدادات البيئة مع
الحفاظ على القواعد السابقة؛ حفظ المسودة لا يفعّل الشبكة أو ينشر البيئة.
تفاصيل الاستجابة 403 ورابط المصدر محفوظة ضمن أدلة M1.

لا صوت معتمد مرخص أو مراجعة تشريحية/تجويدية مستقلة حتى الآن. البطانة الأنفية
في التجربة القديمة مؤلفة وغير مقاسة؛ لا تقدم باعتبارها تصويرًا أو CFD.
