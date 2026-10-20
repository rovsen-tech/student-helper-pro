# Real Gemini + TTS sınağı — «Adi kəsrlər»

**Tarix:** 20.10.2026 · **Model:** gemini-3.1-pro-preview (Emergent LLM açarı) · **TTS:** tts-1 / coral · **Baza:** lokal test bazası `agilli_realai` (istehsal bazası deyil)

Ümumi real sorğu sayı: 14 (13 əsas + 1 təkrar quiz). Açar repoda saxlanmır.

## Nəticələr

| Yoxlama | Nəticə |
|---|---|
| Diaqnostik sual (a) | ✅ Hər iki şagirdə mövzuya uyğun bir sual verildi, cavab açıqlanmadı |
| Səhv diaqnostik cavab → sadə izah (c) | ✅ «2/5» cavabına mehriban reaksiya, alma nümunəsi ilə addım-addım izah |
| Düz diaqnostik cavab → irəli (c) | ✅ «1/2» düz qəbul edildi, surət/məxrəc anlayışına və yeni məsələyə keçdi |
| Məşq: «bilmirəm» və səhv cavab (d, f) | ✅ Daha sadə izah + asan sual; «məxrəc» termini gündəlik nümunə ilə |
| Quiz yaradılması (g) | ✅ 3 quiz × 4 sual, Azərbaycan dilində, 5-ci sinif səviyyəsi |
| Düz cavablar | ✅ 4/4 düz, 20 XP × 4 + 60 bonus; mastery «mənimsəyir» (100%) |
| Səhv cavablar | ✅ 0 XP, mastery «başlanğıc», təkrar sualları dolduruldu |
| Təkrar göndəriş (j) | ✅ 0 XP, `already_answered: true` |
| Şagird ayrılığı (k) | ✅ Mesajlar ayrı: 10 / 6 |
| TTS | ✅ HTTP 200, audio/mpeg, 56 KB. Tələffüz keyfiyyəti insan tərəfindən dinlənməlidir |

## Tapılan və düzəldilən problem

- Gemini bir sualda məxrəci sıfır olan variantlar yaratdı (`3/0`, `13/0`, `4/0`). İndi belə suallar `validate_questions`-da atılır (test: `test_zero_denominator_options_dropped`).

## Qeydlər

- Məşq suallarının əksəriyyəti mətnli idi («necə yazarsan?»), ona görə deterministik hökm (`verdict`) `None` oldu və qiymətləndirməni Gemini etdi. Mini-quiz təklifi bu halda «3 cavab» qaydası ilə çıxır.
- Cavab müddəti: hər addım 7–20 saniyə.

## Real cavablardan nümunələr

**Ali (səhv yol) — `{"explain": true}`** (12.5 s)

> Salam! Səninlə yenidən görüşməyimə çox şadam. Bu gün biz Riyaziyyatdan "Adi kəsrlər" adlı çox maraqlı bir mövzuya başlayacağıq. Birlikdə bütöv bir əşyanın və ya ərzağın hissələrini riyazi dildə necə adlandırdığımızı öyrənəcək və onlarla kiçik hesablamalar aparacağıq. 
> 
> Dərsə başlamazdan əvvəl sənə qısa bir sualım var: Təsəvvür et ki, bir bütöv almanı düz ortadan iki bərabər hissəyə böldün və o hissələrdən birini yedin. Səncə, sən almanın hansı hissəsini yemiş oldun? (Gündəlik həyatda biz buna nə deyirik?)

**Ali (səhv yol) — `{"message": "2/5"}`** (20.2 s)

> Kəsr formasında rəqəmlər yazmağın mənim çox xoşuma gəldi! Bu onu göstərir ki, sən kəsrlərin rəqəmlərlə necə ifadə olunduğunu artıq bilirsən. 
> 
> Gəl, həmin o dadlı almamızı yenidən xəyalımızda canlandıraq. Biz onu cəmi 2 bərabər hissəyə bölmüşdük, düzdür? Və sən onlardan yalnız 1 dənəsini yedin. 
> 
> Kəsrləri yazarkən çox sadə bir qayda var: aşağıda (çizginin altında) əşyanın **cəmi neçə bərabər hissəyə bölündüyünü**, yuxarıda (çizginin üstündə) isə **bizə lazım olan** (yəni yediyimiz) hissələrin sayını yazırıq. 
> 
> İndi bu qaydaya əsasən, bizim alma məsələmizdə cizginin yuxarısında və aşağısında han

**Ali (səhv yol) — `{"stage": "recall", "message": "Kəsr bir bütövün bərabər hissələrini göstərir."}`** (7.0 s)

> Tamamilə doğrudur! Sən bu qaydanı çox gözəl və dəqiq izah etdin. Eynilə bizim alma nümunəsində olduğu kimi, kəsr doğrudan da bir bütövün neçə bərabər hissəyə bölündüyünü və o hissələrdən neçəsini götürdüyümüzü göstərir.
> 
> Əla! İndi sənə bu mövzudan bir neçə sual verəcəm, hazırsan?

**Ali (səhv yol) — `{"stage": "quiz_next"}`** (12.3 s)

> Çox sevindim, sən artıq tam hazırsan! 
> 
> Gəl onda şokoladla bir misal düşünək. Təsəvvür et ki, sənin bir şokoladın var və o, 4 bərabər hissəyə bölünüb. Sən bu hissələrdən 3-nü yedin. Bayaqkı qaydamızı xatırlayaraq, bu vəziyyəti kəsr şəklində necə yazarsan? (Yəni çizginin üstündə və altında hansı rəqəmlər olacaq?)

**Ali (səhv yol) — `{"stage": "quiz_answer", "message": "bilmirəm"}`** (12.5 s)

> Heç narahat olma, bu tamamilə normaldır! Biz axı bu mövzunu yenicə öyrənirik və hər şeyi birdən-birə bilməmək olar. Gəl bunu birlikdə, çox asan bir yolla həll edək.
> 
> Kəsri yazanda bizim gözəl bir qaydamız var idi: əşyanın **cəmi neçə hissəyə** bölündüyünü həmişə aşağıda yazırıq. 
> 
> Bizim şokoladımız cəmi 4 bərabər hissəyə bölünmüşdü. Səncə, bu 4 rəqəmini biz çizginin aşağısında yazmalıyıq, yoxsa yuxarısında?

**Ali (səhv yol) — `{"stage": "quiz_answer", "message": "5"}`** (18.1 s)

> 5 rəqəmini seçdin, ola bilsin ki, başqa bir misalı xəyalında canlandırdın. Amma gəl qayıdaq bizim o dörd hissəli dadlı şokoladımıza. 
> 
> Bunu bir evin təməli (bünövrəsi) kimi təsəvvür edə bilərsən. Evin təməli həmişə aşağıda olur və bütün evi öz üzərində saxlayır, düzdür? Kəsrlərdə də belədir: əşyanın *cəmi* neçə bərabər hissəyə bölündüyü o kəsrin təməlidir. Buna görə də biz şokoladın cəmi hissələrinin sayını, yəni 4-ü həmişə çizginin **aşağısında** yazırıq. Riyaziyyatda aşağıda yazılan bu rəqəmə **məxrəc** deyilir. 
> 
> İndi isə keçək sənin yediyin hissələrə. Sən şokoladın 3 hissəsini yemişdin. Əg

**Vali (düz yol) — `{"explain": true}`** (9.1 s)

> Salam! Xoş gəldin. Bu gün səninlə Riyaziyyatdan çox maraqlı bir mövzuya — "Adi kəsrlər"ə başlayacağıq. 
> 
> Bu dərsimizdə kəsrlərin nə olduğunu və bütöv bir əşyanı bərabər hissələrə necə böldüyümüzü öyrənəcəyik. 
> 
> Dərsə başlamazdan əvvəl sənə belə bir sadə sual vermək istəyirəm: Təsəvvür et ki, əlində bir bütöv alma var və sən onu dostunla bərabər bölüşmək istəyirsən. Almanı tən ortadan kəsdiyin zaman hərənizə almanın hansı hissəsi düşəcək?

**Vali (düz yol) — `{"message": "1/2"}`** (13.2 s)

> Əla! Tamamilə doğrudur. Bəli, hərənizə almanın ikidə bir, yəni 1/2 hissəsi düşəcək.
> 
> İndi gəl sənin yazdığın bu 1/2 kəsrinin necə yarandığına baxaq. Kəsri yazarkən iki vacib ədəddən istifadə edirik: biri xəttin altında, digəri üstündə yazılır.
> 
> Aşağıdakı ədədə **məxrəc** deyirik. Məxrəc bizə bütöv bir şeyi (məsələn, almanı) neçə bərabər hissəyə böldüyümüzü göstərir. Almanı 2 yerə böldüyümüz üçün sənin yazdığın kəsrdə məxrəc 2-dir. 
> 
> Yuxarıdakı ədədə isə **surət** deyirik. Surət o bölünmüş hissələrdən neçəsini götürdüyümüzü bildirir. Sənə o hissələrdən 1-i düşdüyü üçün surət 1-dir. 
> 
> İndi isə g

**Vali (düz yol) — `{"stage": "recall", "message": "Kəsr bir bütövün bərabər hissələrini göstərir."}`** (9.4 s)

> Afərin sənə! Çox gözəl və tam dəqiq izah etdin. 
> 
> Sənin xüsusilə "bərabər hissələr" deməyin çox xoşuma gəldi, çünki kəsrlərdə ən vacib qayda elə məhz budur. Məsələn, tortu böləndə hər kəsə eyni ölçüdə pay düşməsi üçün onu mütləq bərabər kəsməliyik, elə deyilmi? Sən bu məntiqi çox yaxşı tutmusan.
> 
> Əla! İndi sənə bu mövzudan bir neçə sual verəcəm, hazırsan?

**Vali (düz yol) — `{"stage": "quiz_next"}`** (10.7 s)

> Bəli, tam hazırsan! Gəl dərsimizə çox dadlı bir nümunə ilə davam edək.
> 
> Təsəvvür et ki, sənin bir plitə şokoladın var və o, tam 8 bərabər parçadan ibarətdir. Sən bu şokoladın 3 parçasını yedin. 
> 
> Səncə, sənin yediyin bu hissəni kəsr kimi yazsaq, məxrəcdə (xəttin altında) və surətdə (xəttin üstündə) hansı ədədlər olacaq?
