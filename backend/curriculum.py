"""Static 5th-grade Azerbaijan curriculum data (no LLM, no DB).

Topic names must match SUBJECTS topics in server.py.
"""


def _t(order, outcomes, concepts, mistakes, problems):
    return {
        "difficulty_order": order,
        "learning_outcomes": outcomes,
        "key_concepts": concepts,
        "common_mistakes": mistakes,
        "sample_problems": [{"question": q, "answer": a} for q, a in problems],
    }


CURRICULUM = {
    "Riyaziyyat": {
        "Natural ədədlər": _t(
            1,
            ["Çoxrəqəmli natural ədədləri oxuyur və yazır",
             "Natural ədədləri müqayisə edir və yuvarlaqlaşdırır",
             "Dörd əməli (toplama, çıxma, vurma, bölmə) yerinə yetirir"],
            ["rəqəm", "mərtəbə", "sinif", "müqayisə", "yuvarlaqlaşdırma", "əməllərin ardıcıllığı"],
            ["Ədədin içindəki sıfırı unudur (məsələn, 3 045 əvəzinə 345 yazır)",
             "Əməllərin ardıcıllığını pozur: vurmadan əvvəl toplayır",
             "Yuvarlaqlaşdırmada 5 rəqəmini aşağı yuvarlaqlaşdırır"],
            [("25 + 15 × 2 neçədir?", "55"),
             ("4 725 ədədini yüzlüklərə qədər yuvarlaqlaşdır.", "4 700"),
             ("Hansı böyükdür: 10 099 yoxsa 10 909?", "10 909")],
        ),
        "Adi kəsrlər": _t(
            2,
            ["Kəsrin surətini və məxrəcini tanıyır",
             "Eyni məxrəcli kəsrləri toplayır və çıxır",
             "Kəsrləri müqayisə edir və ixtisar edir"],
            ["surət", "məxrəc", "düzgün kəsr", "düzgün olmayan kəsr", "qarışıq ədəd", "ixtisar"],
            ["Kəsrləri toplayanda məxrəcləri də toplayır (1/4 + 1/4 = 2/8)",
             "Məxrəci böyük olan kəsrin daha böyük olduğunu düşünür",
             "Məxrəcin sıfır ola biləcəyini düşünür"],
            [("1/4 + 2/4 neçədir?", "3/4"),
             ("Hansı böyükdür: 1/3 yoxsa 1/5?", "1/3"),
             ("6/8 kəsrini ixtisar et.", "3/4")],
        ),
        "Onluq kəsrlər": _t(
            3,
            ["Onluq kəsrləri oxuyur və yazır",
             "Onluq kəsrləri toplayır və çıxır",
             "Onluq kəsri adi kəsrə çevirir"],
            ["vergül", "onda bir", "yüzdə bir", "tam hissə", "kəsr hissə"],
            ["Toplayanda vergülləri bir-birinin altına yazmır",
             "0,5 ilə 0,50-nin fərqli ədədlər olduğunu düşünür",
             "Rəqəmi çox olan onluq kəsrin böyük olduğunu düşünür (0,25 > 0,3)"],
            [("0,3 + 0,45 neçədir?", "0,75"),
             ("0,5 hansı adi kəsrə bərabərdir?", "1/2"),
             ("Hansı böyükdür: 0,3 yoxsa 0,25?", "0,3")],
        ),
        "Faiz": _t(
            4,
            ["Faizin bütövün yüzdə bir hissəsi olduğunu başa düşür",
             "Ədədin faizini tapır",
             "Faizi kəsrlə əlaqələndirir (50% = 1/2)"],
            ["faiz", "yüzdə bir", "bütöv = 100%", "hissə"],
            ["Faizi adi ədəd kimi toplayır, bütövü nəzərə almır",
             "50%-in yarı olduğunu unudur",
             "Ədədin faizini taparkən 100-ə bölməyi unudur"],
            [("200-ün 10%-i neçədir?", "20"),
             ("50% hansı kəsrə bərabərdir?", "1/2"),
             ("40 manatın 25%-i neçə manatdır?", "10 manat")],
        ),
        "Həndəsi fiqurlar": _t(
            5,
            ["Düzbucaqlı, kvadrat və üçbucağı tanıyır",
             "Düzbucaqlının və kvadratın perimetrini tapır",
             "Düzbucaqlının sahəsini tapır"],
            ["nöqtə", "düz xətt", "bucaq", "perimetr", "sahə", "kvadrat", "düzbucaqlı"],
            ["Perimetr ilə sahəni qarışdırır",
             "Sahəni kvadrat vahidlə (sm²) yazmağı unudur",
             "Perimetri taparkən yalnız iki tərəfi toplayır"],
            [("Tərəfi 5 sm olan kvadratın perimetri neçədir?", "20 sm"),
             ("Uzunluğu 6 sm, eni 4 sm olan düzbucaqlının sahəsi neçədir?", "24 sm²"),
             ("Üçbucağın neçə bucağı var?", "3")],
        ),
        "Ölçü vahidləri": _t(
            6,
            ["Uzunluq, kütlə və zaman vahidlərini tanıyır",
             "Bir vahidi digərinə çevirir",
             "Gündəlik məsələlərdə ölçü vahidlərindən istifadə edir"],
            ["millimetr", "santimetr", "metr", "kilometr", "qram", "kiloqram", "dəqiqə", "saat"],
            ["1 metrin 10 santimetr olduğunu düşünür (düzgünü 100 sm)",
             "Fərqli vahidləri çevirmədən toplayır",
             "1 saatın 100 dəqiqə olduğunu düşünür"],
            [("3 metr neçə santimetrdir?", "300 sm"),
             ("2 kiloqram neçə qramdır?", "2000 q"),
             ("2 saat neçə dəqiqədir?", "120 dəqiqə")],
        ),
        "Sadə tənliklər": _t(
            7,
            ["Tənliyin nə olduğunu başa düşür",
             "Məchul toplananı, azalanı və vuruğu tapır",
             "Cavabı yerinə qoyub yoxlayır"],
            ["tənlik", "məchul", "kök", "yoxlama", "tərs əməl"],
            ["x + 5 = 12 tənliyində 5-i çıxmaq əvəzinə toplayır",
             "Cavabı yoxlamır",
             "Vurma ilə bölmənin tərs əməl olduğunu unudur"],
            [("x + 5 = 12. x neçədir?", "7"),
             ("3 · x = 18. x neçədir?", "6"),
             ("x − 4 = 10. x neçədir?", "14")],
        ),
    },
    "Azərbaycan dili": {
        "Səslər və hərflər": _t(
            1,
            ["Sait və samit səsləri fərqləndirir", "Əlifbanı ardıcıl söyləyir"],
            ["səs", "hərf", "sait", "samit", "əlifba"],
            ["Səslə hərfi eyni şey hesab edir", "Qalın və incə saitləri qarışdırır"],
            [("Azərbaycan əlifbasında neçə hərf var?", "32"),
             ("«Ana» sözündə neçə sait var?", "2")],
        ),
        "İsim": _t(
            3,
            ["İsmin əşya, şəxs və hadisə bildirdiyini başa düşür", "Ümumi və xüsusi isimləri fərqləndirir"],
            ["isim", "kim?", "nə?", "harada?", "ümumi isim", "xüsusi isim"],
            ["Xüsusi isimləri kiçik hərflə yazır", "Sifəti isim hesab edir"],
            [("«Bakı» ümumi isimdir, yoxsa xüsusi?", "xüsusi"),
             ("İsim hansı suallara cavab verir?", "kim? nə? harada?")],
        ),
        "Sifət": _t(
            4,
            ["Sifətin əlamət bildirdiyini başa düşür", "Sifəti isimlə birlikdə işlədir"],
            ["sifət", "necə?", "hansı?", "əlamət"],
            ["Sifəti fellə qarışdırır", "Sifətin sualını səhv verir"],
            [("«Qırmızı alma» birləşməsində sifət hansıdır?", "qırmızı"),
             ("Sifət hansı suallara cavab verir?", "necə? hansı?")],
        ),
        "Fel": _t(
            5,
            ["Felin iş və hərəkət bildirdiyini başa düşür", "Felin zamanını müəyyən edir"],
            ["fel", "nə etdi?", "nə edir?", "zaman"],
            ["İsmi fel hesab edir (məsələn, «qaçış»)", "Keçmiş və gələcək zamanı qarışdırır"],
            [("«Uşaq qaçır» cümləsində fel hansıdır?", "qaçır"),
             ("«Oxudu» feli hansı zamandadır?", "keçmiş zaman")],
        ),
    },
    "Təbiət": {
        "Canlılar aləmi": _t(
            1,
            ["Canlı və cansızı fərqləndirir", "Canlıların əsas əlamətlərini sadalayır"],
            ["canlı", "cansız", "qidalanma", "tənəffüs", "böyümə", "çoxalma"],
            ["Hərəkət etməyən hər şeyi cansız sayır (bitkilər canlıdır)", "Günəşi canlı hesab edir"],
            [("Bitki canlıdır, yoxsa cansız?", "canlı"),
             ("Canlıların bir əlamətini de.", "böyümə")],
        ),
        "Bitkilər": _t(
            2,
            ["Bitkinin hissələrini sadalayır", "Bitkinin yaşamaq üçün nəyə ehtiyacı olduğunu bilir"],
            ["kök", "gövdə", "yarpaq", "çiçək", "meyvə", "toxum", "işıq", "su"],
            ["Bitkinin qidanı yalnız torpaqdan aldığını düşünür", "Kökün funksiyasını bilmir"],
            [("Bitki suyu hansı hissəsi ilə alır?", "kök"),
             ("Bitkinin böyüməsi üçün nə lazımdır?", "su, işıq, hava")],
        ),
        "Günəş sistemi": _t(
            5,
            ["Günəş sisteminin planetlərini sadalayır", "Gecə və gündüzün səbəbini izah edir"],
            ["Günəş", "planet", "Yer", "Ay", "orbit", "fırlanma"],
            ["Günəşin Yerin ətrafında fırlandığını düşünür", "Ayı planet hesab edir"],
            [("Yer Günəşin ətrafında neçə vaxta bir dövr edir?", "1 il"),
             ("Ay planetdir, yoxsa peyk?", "peyk")],
        ),
    },
}


def get_topic_info(subject, topic):
    info = CURRICULUM.get(subject or "", {}).get(topic or "")
    if info is None:
        return None
    return {"subject": subject, "topic": topic, **info}


def get_subject_topics_ordered(subject):
    topics = CURRICULUM.get(subject or "", {})
    return [name for name, _ in sorted(topics.items(), key=lambda kv: kv[1]["difficulty_order"])]
