# مخارج — تنفيذ الخطة الهندسية

الخطة المعتمدة: [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md).
تفاصيل الاستكمال: [WORKING_STATE.md](docs/WORKING_STATE.md).

**اكتملت تهيئة M0. رفض المستخدم واقعية التشريح الداخلي في دراسة M2، ويجري إعادة بنائه.**
يوجد رأس متصل مع أعضاء الفم والأنف والبلعوم وسياق للحنجرة، في ملف Blender
قابل للتحرير وGLB فعلي. لم تُقبل بعد جودة اتصال الأنسجة والواقعية النهائية،
ولا يوجد تجهيز جديد للحروف الخمسة. التطبيق الحالي يعرض التجربة التقنية السابقة.

[معاينة الدراسة المرفوضة المحفوظة للمقارنة](artifacts/milestone-evidence/M2/character-assembly/browser-review.png)
· [دوران الحجم الحقيقي](artifacts/milestone-evidence/M2/character-assembly/volume-rotation.gif)

## التشغيل

الإصدارات المختبرة: Node 24.19.0، npm 11.9.0، Blender 4.3.2 وPython 3.12.
حزم الهندسة الأصلية منفصلة عن Python المضمن في Blender.

```sh
npm ci --no-audit --no-fund
python -m venv --system-site-packages .venv-qa
.venv-qa/bin/python -m pip install -r scripts/qa/requirements.txt
npm run build
npm run test:unit
npm run preview -- --port 4173 --strictPort
```

مع Chromium مثبت في `/usr/bin/chromium`، يفحص `npm run test:e2e` النموذج القديم
فعليًا في المتصفح: تحميل الملف، تغير الوضع، العودة إلى البداية وأخطاء JavaScript.
هذا لا يعتمد التشريح الجديد.

## إنتاج ومراجعة التجميع الجديد

```sh
npm run assets:export
npm run assets:validate
npm run test:geometry
npm run evidence:capture
npm run package:source
```

- `assets:export` يعيد إنشاء المعايرة والفراغات والتجميع، ويفحص الفراغات قبل
  عمليات القص، ثم يقارن هندسة GLB الفعلية بالمصدر. المخرج مسودة M2.
- `assets:validate` يفحص المصادر الأصلية والأسطح والملف المصدّر، ثم يطبّق
  بوابة M2. **يرجع فشلًا ما دامت مهام الربط والمراجعة البنيوية مفتوحة.**
- `test:geometry` يشغّل اختبارات محولات الهندسة وفحص الفراغات وبوابة M2 نفسها.
  نجاح اختبارات المثلثات لا يمسح مهام التشريح المفتوحة.
- `evidence:capture` ينتج ست زوايا فعلية في Blender ومعاينة بحجمين في متصفح
  واحد وثماني زوايا دوران. هذا عارض فحص مستقل عن واجهة المنتج.
- `package:source` ينشئ ZIP مع التحقق من CRC وبصمات كل الملفات في
  `/workspace/artifacts/makharij-source.zip`، دون الحزم المؤقتة أو الأسرار.

ملفات العمل والأدلة في
`artifacts/milestone-evidence/M2/character-assembly`، وأهمها
`character-assembly.blend` و`character-assembly.glb` و`assembly.manifest.json`.
الأحجام بالمتر والمحاور +X للأمام و+Y للأعلى و+Z لليمين. ملفات الدراسة في
Blender تستخدم هذا الإطار صراحة، والتصدير لا يكرر تحويل المحاور.

`npm run assets:inspect -- --input PATH --out PATH` يفحص ملفات Blender/OBJ/GLB
بقراءة فعلية دون تعديلها. `npm run typecheck` يفحص TypeScript.

## المصادر وحدود النموذج

الأصول الأصلية المرخصة وبصماتها في `assets/source`: عددها 78 ملفًا عبر ثلاث
لقطات مثبتة. أصول الرأس والعيون واستهدافات MakeHuman هي CC0؛ شيفرة تطبيقه
AGPL ليست جزءًا من المنتج. مصادر ArtiSynth محفوظة بإشعاراتها وترخيص البيانات.
تُفحص 6 حدود رباعيات سطوح مقابل أحجام الخلايا الأصلية بصورة مستقلة.

التجميع إعادة بناء من مصادر مستقلة. المعايرة والتشوهات الفنية موثقة ولا تثبت
تسجيلًا سريريًا أو متبرعًا واحدًا. البطانة الأنفية والمحارات وامتداد المجرى
السفلي أجزاء مؤلفة وغير مقاسة. العضلات فوق اللامية سياق للأرضية، والغضاريف
سياق للحنجرة؛ لا تُقدَّم كأرضية مخاطية كاملة أو أحبال صوتية.

الحزمة الاختيارية المحجوبة من MakeHuman لم تعد تعطل العمل؛ اختير مسار إعادة
البناء من الأصول المتاحة. لم نستخدم وسيطًا لتجاوز الحجب. لا توجد مراجعة علمية
أو تجويدية مستقلة أو أصوات نهائية معتمدة بعد.

فرع العمل `codex/anatomy-foundation-v2` محفوظ على GitHub. لا دمج في الفرع
الرئيسي ولا نشر للموقع. قرار المصادر وتفاصيل ما بقي في
[ASSET_DECISION.md](docs/ASSET_DECISION.md) و[ANATOMY_SPEC.md](docs/ANATOMY_SPEC.md).
