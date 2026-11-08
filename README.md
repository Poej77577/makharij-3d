# مخارج — تجربة الفم والوجه المتحرك

المعاينة على **`/mouth.html`**: وجه بشري متصل من أصل CC0، وثمانية متحكمات
للفك واللسان والحنك والشفتين، وعرض داخلي ومقطع يتغير مع التشوه. فتح الفك
يحرك الجلد والأسنان بحالة مشتركة واحدة. **الداخل ما زال مبسّطًا، ولم يُقبل
تشريحًا نهائيًا أو وضعيات حروف معتمدة.**

[الواجهة](artifacts/method-evidence/oral-sculpt/browser/desktop.png)
· [حركة الشفتين](artifacts/method-evidence/oral-sculpt/browser/lip-motion.gif)
· [الفم والفحوص](docs/ORAL_SCULPT_REVIEW.md)
· [الوجه وحدوده](docs/FACE_CONTEXT_REVIEW.md).

أصلح الفحص المستقل اختراقات اللسان للأسنان: من 17 زوجًا متقاطعًا إلى صفر
ضمن 36 زوجًا مختبرًا. نجحت كذلك 20 مقارنة بين سطح الوجه والأسنان؛ هذه
نتائج هندسية محددة، ولا تعني اعتماد الشكل أو صحة مخارج الحروف.

```sh
npm run assets:oral:validate
npm run test:unit
npm run build
npm run preview -- --port 4174 --strictPort
# ثم افتح /mouth.html. إعادة بناء المصدر موثقة في ORAL_SCULPT_REVIEW.md.
```

## الدراسات السابقة المحفوظة

**رفض المستخدم أيضًا واقعية إعادة بناء الأطلس. هذه الملفات محفوظة للمقارنة، وليست الأصل المختار للمنصة.**

المسار الجديد ونتائج فحص البدائل: [ANIMATABLE_ASSET_ROUTE.md](docs/ANIMATABLE_ASSET_ROUTE.md).
مواصفات الأصل المطلوب: [ANATOMICAL_ASSET_BRIEF.en.md](docs/ANATOMICAL_ASSET_BRIEF.en.md).

أُنجز نقاش مع اجنت واحد وتجربة أصلية صغيرة لتحريك اللسان باستخدام مهارة
Blender مفتوحة المصدر. **فشل الشكل بعد تصحيح واحد، وأُوقف اعتماده**؛
نجح التصدير الحركي فقط. [الصور والنتيجة والخطوة التالية](docs/TONGUE_PILOT_REVIEW.md).
الأصل التالي نحت تشريحي متخصص؛ يمكن تجهيزه للحركة بعد قبول هيئته.

أُعيد بناء الداخل في الدراسة التاريخية بعد رفض واقعية النموذج السابق. الأساس الجديد هو الأجزاء
الفعلية من Z-Anatomy / BodyParts3D في إطار تشريحي مشترك، مع رأس MakeHuman
متصل. يوجد لسان وجذر متصلان، ولثة وأسنان وحنك ولهاة وبنى أنفية وبلعومية
وسياق للحنجرة. النموذج في وضع الراحة؛ التحريك والمراجعة العلمية قيد العمل.

افتح **`/anatomy.html`** لمراجعة الدراسة المرفوضة وتدويرها وتكبير أجزائها. يعرض
المقاطع أحجام الأنسجة الفعلية، محسوبة من GLB، مع مستوى أنفي إضافي يُظهر المحارات.
تبقى الدراسة التقنية القديمة على `/` للمقارنة.

[المقطع الجديد](artifacts/milestone-evidence/M2/realistic-rebuild/atlas-mouth.png)
· [المعاينة في المتصفح](artifacts/milestone-evidence/M2/realistic-rebuild/browser-review.png)
· [خطة التنفيذ](docs/IMPLEMENTATION_PLAN.md)
· [حالة العمل](docs/WORKING_STATE.md)

## التشغيل

الإصدارات: Node 24.19.0، npm 11.9.0، Blender 4.3.2، Python 3.12.
حزم الهندسة منفصلة عن Python المضمن في Blender.

```sh
npm ci --no-audit --no-fund
python -m venv --system-site-packages .venv-qa
.venv-qa/bin/python -m pip install -r scripts/qa/requirements.txt
npm run build
npm run preview -- --port 4173 --strictPort
```

## إعادة البناء والفحص

```sh
npm run assets:export
npm run assets:validate
npm run test:geometry
npm run test:unit
npm run build
npm run test:e2e
npm run evidence:capture
npm run package:source
```

- `assets:export` يعيد بناء الأنسجة والجذر والرأس والتجاويف، ويخبز تفاصيل
  سطح اللسان، ثم يفحص GLB ويضعه مع المقاطع المطابقة في صفحة المراجعة.
- `assets:validate` و`test:geometry` يفحصان الملف الفعلي والفراغات واتصال
  الجذر والتداخل مع الأسنان والفك. يفشلان عند وجود خلل فعلي.
- `assets:acceptance` بوابة القبول النهائية؛ **تفشل ما دامت المراجعة
  البصرية والعلمية معلّقة**. نجاح الهندسة لا يمنح اعتمادًا تشريحيًا.
- `test:e2e` يفحص الصفحة الجديدة والتحكم والدوران وهوية الملف في Chromium،
  إضافة إلى الدراسة التقنية السابقة. يتطلب خادم المعاينة وChromium في
  `/usr/bin/chromium`. هذا لا يقيس أداء هاتف فعلي.
- `package:source` ينتج `/workspace/artifacts/makharij-source.zip` مع التحقق
  من CRC وبصمات الملفات، دون الحزم المؤقتة أو الأسرار.

ملفات Blender وGLB والتقارير والصور في
`artifacts/milestone-evidence/M2/realistic-rebuild`. المصدر الداخلي
`internal-rest.blend`، والنتيجة المركبة `atlas-study.blend` و`atlas-study.glb`.
الأصول المختارة محفوظة دون تغيير في `assets/source/z-anatomy`.
الدراسة المرفوضة محفوظة في `M2/character-assembly` ولا يُستخدم شكلها في
إعادة البناء الجديدة.

الإطار بالمتر: +X للأمام، +Y للأعلى، +Z ليمين الشخص. يتلقى الداخل إزاحة
واحدة عند تركيب الرأس؛ لا تمديد منفصل للحلق. إصلاحات الأنسجة والسماكات
ومواءمة دهليز الفم والفراغات والخامات موثقة في manifest.

## المصادر والترخيص

النموذج التشريحي المعدّل **CC BY-SA 4.0**، مع الإسناد وإشعار التعديلات
والمشاركة بالمثل لبيانات النموذج. الرأس والعينان الأصليان **CC0**.
ترخيص بيانات النموذج لا يعيد ترخيص شيفرة التطبيق المستقلة.

- BodyParts3D — The Database Center for Life Science — CC BY-SA 2.1 Japan.
- Z-Anatomy — The libre 3D atlas of anatomy — CC BY-SA 4.0.
- [الإشعارات والتفاصيل](assets/source/z-anatomy/NOTICE.md).

أصول الأذن الداخلية والكلية والدماغ ذات التراخيص المنفصلة غير مشمولة،
ولا شيفرة قالب الأطلس أو تعريفات Wikipedia. الرأس والداخل ليسا مسحًا
سريريًا لمتبرع واحد. التخطيط الليفي وتفاصيل سطح اللسان توضيحية، والغضاريف
ليست أحبالًا صوتية. لا توجد مراجعة علمية أو تجويدية نهائية بعد.

فرع العمل `codex/anatomy-foundation-v2`؛ لا دمج رئيسي ولا نشر عام.
