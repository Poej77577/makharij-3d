# نتيجة تجربة اللسان ومراجعة الطريقة — 2026-11-07

**فشل الشكل بعد تجربة أولى وتصحيح واحد. لا يُعتمد هذا اللسان أصلًا للطلاب،
ولا تبدأ دورة ثالثة لتزيينه أو توسيعه إلى رأس كامل.** هذه مراجعة هندسية
للشكل من المنسق واجنت منفصل؛ ليست موافقة طبيب أو مختص مخارج.

[لوحة الصور الفعلية](../artifacts/method-evidence/tongue-pilot/review-sheet.png)
· [نقد الاجنت](../artifacts/method-evidence/tongue-pilot/independent-pilot-review.md)
· [قرار قابل للفحص مع البصمات](../artifacts/method-evidence/tongue-pilot/visual-review.json)

## ما جُرّب

بناء أصلي صغير، بمقاطع سهمية وعرضية صريحة، وشبكة واحدة مستمرة للطرف
والظهر والسطح البطني والجذر. لم يُستخدم لسان الأطلس، أو Boolean/Remesh،
أو زخرفة سطحية لتغطية الهيئة. ثُبتت الشبكة قبل إضافة ثلاثة Shape Keys:
رفع الطرف، رفع الظهر، وسحب الجذر. كل الأبعاد واتساع العرض وشدة الحركة
افتراضات تشكيلية، وليست قياسات من MRI أو من صورة المستخدم.

صُوّر الأصل بخامة محايدة من الجانب والأعلى والأسفل وثلاثة أرباع، ثم في
سياق الأسنان واللثة. أسنان/لثة Z-Anatomy مرجع قياس مرخّص فقط، بلا ادعاء
تسجيل سريري؛ الأرضية والحنك سطحان إرشاديان مفتوحان وموسومان كذلك. لا
يُصدَّر هذا السياق إلى GLB الخاص باللسان. المقاطع صور لهندسة مقطوعة
فعليًا في نسخة مراجعة منفصلة؛ لم تتغير شبكة التحريك لصناعة الصور.

استُخدمت مهارة [Blender image to 3D](../.agents/skills/blender-image-to-3d/SKILL.md)
من [المصدر MIT](https://github.com/majidmanzarpour/blender-game-skills)، بالإصدار
المثبت في `UPSTREAM.json`. تكيفها المحلي موثّق، وتشغيل شيفرة ملفات Blender
المرفقة معطل. المهارة تدير التصوير والتسليم؛ لا تمنح خبرة تشريحية آليًا.

## لماذا رُفض

- في البداية كان الطرف حادًا، والانتقال بين الظهر والجانب يبدو كحافة غطاء.
- بعد تدوير المقاطع والطرف صار الطرف فصًا محاطًا بثنية؛ كشف رفعه انثناءً
  يشبه المفصل بدل انتقال نسيجي سلس. بقيت نهايات العرض منكمشة ومصطنعة.
- الجذر كتلة عامة تمتد وراء/أسفل دليل القاع، بلا اتصال مخاطي مقروء.
  وجود أسطح الحنك والقاع الإرشادية لا يثبت تشريح الفم أو سماكة أنسجته.

الحكم الكامل مع صور محددة وبصماتها في `independent-pilot-review.json`.
التصحيح الوحيد استُنفد؛ لا نضيف حليمات أو خامات أو مزيدًا من Remesh.

## ما نجح تقنيًا وحدوده

أُعيد استيراد GLB الفعلي إلى مشهد Blender نظيف. قورنت رؤوس السطح بالأصل
في عشر حالات: الراحة، نصف وشدة كل تحكم، وفواصل العودة. وصلت المفاتيح
الثلاثة بأسمائها، ووصل التسلسل الحركي. أقصى فرق في مقارنة الرؤوس كان
`0 m`، والعودة إلى الراحة `0 m` في هذه العينة.

[التقرير الفعلي](../artifacts/method-evidence/tongue-pilot/revision-1/morph-roundtrip.json)
يثبت تطابق هذا التصدير فقط. لا يفحص حفظ حجم العضلات، أو كل تقاطعات
الأسنان، أو تماس النطق، ولا يجعل الشكل واقعيًا. تُحفظ التجربة كعينة
تقنية مرفوضة بصريًا لتطوير أدوات إدخال الأصول والتصدير.

## القرار التنفيذي

نحتاج **أصلًا تشريحيًا فنيًا متخصصًا، ولو ثابتًا**. نبدأ بعينة الفم المحددة
في [مواصفات الاستلام](ANATOMICAL_ASSET_BRIEF.en.md)، ونفحص الملف الحقيقي
والحقوق والسطح البطني والجذر والقاع. بعد قبول الهيئة نبني Retopology
وشبكة تحكم ترتبط بالنحت، ثم مفاتيح التشوه وتصحيحات التماس والتصدير.
لا نشترط Rig جاهزًا لشراء/اكتساب نحت جيد، ولا نقبل avatar متحركًا ضعيف الداخل.

لم يُكتسب بعد أصل متخصص مؤهل، ولم يُفحص سعر/عرض تجاري أو يُشتر شيء.
الوصول لبعض المتاجر ما زال محجوبًا بسياسة البيئة كما هو موثق في
`ANIMATABLE_ASSET_ROUTE.md`. لا تدّعي هذه التجربة إتمام النموذج أو M2/M3.

## إعادة الإنتاج

المخرجات المفحوصة محفوظة؛ استخدم مجلدًا منفصلًا كي لا تستبدل أدلة المراجعة:

```sh
blender --background --factory-startup --disable-autoexec --threads 2 --python-exit-code 1 --python tools/blender/build_tongue_pilot.py -- --revision rounded-sections --out artifacts/method-evidence/tongue-pilot/reproduced
blender --background --factory-startup --disable-autoexec --threads 2 --python-exit-code 1 --python tools/blender/render_tongue_pilot.py -- --folder artifacts/method-evidence/tongue-pilot/reproduced --stage review --poses
blender --background --factory-startup --disable-autoexec --threads 2 --python-exit-code 1 --python tools/blender/check_morph_roundtrip.py -- --blend artifacts/method-evidence/tongue-pilot/reproduced/tongue-pilot.blend --glb artifacts/method-evidence/tongue-pilot/reproduced/tongue-pilot.glb --object PILOT_TONGUE --out artifacts/method-evidence/tongue-pilot/reproduced/morph-roundtrip.json
```

`--revision baseline` يعيد التجربة الأولى. لا تعني إعادة الإنتاج إعادة
اعتماد الشكل. صفحة المنتج تبقى موسومة برفض الدراسة التاريخية، ولم يُدمج
هذا اللسان فيها.
