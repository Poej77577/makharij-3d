/** Source-calibrated technical Ra prototype, not qualified recitation review. */
export const raDuration=3.2;
export const raKeys=['ra_prepared','ra_contact'];
function smooth(u:number){u=Math.max(0,Math.min(1,u));return u*u*(3-2*u)}
export function sampleRa(t:number):{weights:Record<string,number>;phase:string}{
 let prep=0,lift=0,phase='راحة';
 if(t>=.08&&t<.26){prep=smooth((t-.08)/.18);phase='تهيؤ وتراجع الطرف'}
 else if(t>=.26&&t<.40){prep=1;lift=smooth((t-.26)/.14);phase='اقتراب من المنطقة اللثوية'}
 else if(t>=.40&&t<.42){prep=1;lift=1;phase='تحقيق تقني للمخرج — قيد المراجعة'}
 else if(t>=.42&&t<.70){prep=1;lift=1-smooth((t-.42)/.28);phase='تحرير'}
 else if(t>=.70&&t<.86){prep=1-smooth((t-.70)/.16);phase='عودة'}
 return {weights:{ra_prepared:prep-lift,ra_contact:lift},phase};
}
