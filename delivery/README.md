# حزمة فحص نموذج الراحة

**بوابة إثبات التشريح لم تُجتز؛ حركات الحروف الخمس وبقية المنصة غير جاهزة.**

- [تنزيل حزمة المصدر وBlender ونسخة المتصفح والأدلة](./makharij-anatomy-source.zip) — افتح الملف ثم استخدم زر Download / View raw في GitHub.
- [حالة العمل وحدود الفحص](../docs/STATUS.md)
- [المعاينة المكتبية الفعلية](../public/evidence/browser-desktop.png)
- [المقطع الجانبي](../public/evidence/rest-side.png)
- [فيديو الدوران من GLB داخل المتصفح](../public/evidence/rest-rotation.mp4)
- [التراخيص والمصادر](../docs/PROVENANCE.md)

بعد فك ZIP:

```sh
python3 -m http.server 8080 --directory browser
```

افتح `http://localhost:8080`. البناء من المصدر: `npm ci` ثم `npm run build`. إعادة النموذج: `blender -b -t 2 --python scripts/build_model.py`.

نجحت اختبارات العارض وبناء الإنتاج وفحص طوبولوجيا ملف GLB النهائي. لا مراجعة تشريحية أو تجويدية مستقلة، ولا اختبار هاتف فعلي أو أرقام أداء. الفيديو دوران للمجسم، وليس فيديو نطق.

النسخة مضمنة من الالتزام المبين في manifest.json. استُعيدت الملفات من نسخة GitHub جديدة وطابقت بصماتها النسخة المحلية. لم تُنشر منصة على خدمة استضافة.
