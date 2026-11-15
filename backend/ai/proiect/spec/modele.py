"""Hand-written technical specifications for the frequent kinds of proposal.

Every dimension, quantity and minimum area here is a SCHEMATIC DESIGN ASSUMPTION of this app (a typical order
of magnitude, chosen so that plans are readable and feasibility checks are honest), not a value taken from a
standard, a norm or a product sheet. A licensed designer sets the real ones. Each model says so in `ipoteze`
and names what it leans on in `surse` (general knowledge, public programme guides), never a figure of money.

The seven kinds that already had a drawing catalogue keep the same footprints, so existing plans do not change.
"""
from backend.ai.proiect.spec.model import Componenta as C
from backend.ai.proiect.spec.model import Specificatie

ENERGIE, APA, CANAL = "energie electrică", "apă potabilă", "canalizare"

_BANCI = C(nume="bancă", categorie="mobilier", cantitate=3, latime_m=1.8, lungime_m=0.6, inaltime_m=0.9,
           zona_libera_m=0.5, rol="odihnă pentru vizitatori", articol="banca", tip_desen="banca")
_COSURI = C(nume="coș de gunoi", categorie="mobilier", cantitate=2, latime_m=0.6, lungime_m=0.6, inaltime_m=1.0,
            zona_libera_m=0.3, rol="curățenie", articol="cos_gunoi_stradal", tip_desen="cos")
_ALEE = C(nume="alee de acces pavată", categorie="finisaj", unitate="mp", pe_plan=False, derivat_din="plan_alee",
          rol="acces pietonal, inclusiv pentru cărucioare și scaune rulante", articol="pavaj", tip_desen="alee")
_GARD = C(nume="împrejmuire (gard)", categorie="siguranta", unitate="ml", pe_plan=False, derivat_din="plan_perimetru",
          rol="delimitare și siguranță", articol="gard")
_GAZON = C(nume="spațiu verde (gazon în rulou)", categorie="vegetatie", unitate="mp", pe_plan=False,
           derivat_din="plan_rest", rol="suprafața rămasă liberă, înierbată", articol="gazon_rulou")
_PANOU = C(nume="panou cu regulamentul de folosire", categorie="semnalizare", cantitate=1, latime_m=0.8,
           lungime_m=0.1, inaltime_m=2.0, zona_libera_m=0.3, rol="reguli, program, contact administrator",
           tip_desen="semnalizare")
_ILUMINAT = C(nume="stâlp de iluminat LED", categorie="instalatie", cantitate=2, latime_m=0.3, lungime_m=0.3,
              inaltime_m=4.0, zona_libera_m=0.3, rol="siguranță după lăsarea serii", utilitati=[ENERGIE],
              articol="stalp_iluminat", tip_desen="iluminat")

MODELE: dict[str, Specificatie] = {}


def _add(spec: Specificatie) -> None:
    MODELE[spec.tip_amenajare] = spec


_add(Specificatie(
    tip_amenajare="skatepark", eticheta="skatepark", suprafata_minima_mp=200, suprafata_recomandata_mp=600,
    utilitati_necesare=[ENERGIE], categorie_lucrare=["amenajare_exterioara", "platforma_beton", "iluminat"],
    componente=[
        C(nume="zonă de skate (rampe și obstacole)", categorie="echipament", latime_m=20, lungime_m=15,
          min_latime_m=10, min_lungime_m=8, inaltime_m=1.5, zona_libera_m=1.0, obligatoriu=True,
          rol="platformă din beton cu module (quarter pipe, fun box, grind rail)", tip_desen="skate",
          articol="suprafata_skate"),
        C(nume="zonă pentru începători", categorie="echipament", latime_m=8, lungime_m=6, min_latime_m=5,
          min_lungime_m=4, inaltime_m=0.6, zona_libera_m=1.0, rol="module joase pentru copii", tip_desen="skate",
          articol="suprafata_skate"),
        _ILUMINAT, _BANCI, _COSURI, _PANOU, _ALEE, _GARD, _GAZON,
    ],
    beneficii=["loc sigur pentru sporturi urbane, în locul străzii și al parcărilor",
               "activitate fizică pentru adolescenți și tineri, gratuită",
               "punct de întâlnire pentru comunitate; poate găzdui concursuri locale"],
    riscuri_specifice=["zgomot: distanța față de locuințe și programul de folosire trebuie stabilite",
                       "uzura modulelor cere întreținere periodică și verificări de siguranță"],
    ipoteze=["Platforma din beton și modulele au dimensiuni schematice; proiectul tehnic le dimensionează."],
    surse=["cunoștințe generale despre skateparkuri publice din România; proiectele de referință din dosar"],
))

_add(Specificatie(
    tip_amenajare="loc_de_joaca", eticheta="loc de joacă", suprafata_minima_mp=100, suprafata_recomandata_mp=300,
    utilitati_necesare=[ENERGIE], categorie_lucrare=["amenajare_exterioara", "echipamente_joaca", "iluminat"],
    componente=[
        C(nume="structură de joacă cu tobogan", categorie="echipament", latime_m=6, lungime_m=4, min_latime_m=4,
          min_lungime_m=3, inaltime_m=3.0, zona_libera_m=1.5, obligatoriu=True,
          rol="echipament principal, grupa de vârstă 3-12 ani", articol="complex_joaca", tip_desen="joaca"),
        C(nume="leagăne", categorie="echipament", latime_m=4, lungime_m=2.5, inaltime_m=2.4, zona_libera_m=1.5,
          rol="două locuri, unul pentru copii mici", articol="leagan", tip_desen="joaca"),
        C(nume="nisipar", categorie="echipament", latime_m=3, lungime_m=3, min_latime_m=2, min_lungime_m=2,
          inaltime_m=0.4, zona_libera_m=0.5, rol="joacă pentru cei mici", tip_desen="joaca"),
        C(nume="balansoar", categorie="echipament", latime_m=3, lungime_m=0.6, inaltime_m=0.8, zona_libera_m=1.5,
          rol="joacă în doi", articol="balansoar", tip_desen="joaca"),
        C(nume="pardoseală de protecție (cauciuc / tartan)", categorie="finisaj", unitate="mp", pe_plan=False,
          derivat_din="plan_zona_libera", rol="suprafață amortizoare sub și în jurul echipamentelor",
          articol="pardoseala_cauciuc"),
        _ILUMINAT, _BANCI, _COSURI, _PANOU, _ALEE, _GARD, _GAZON,
    ],
    beneficii=["loc sigur de joacă pentru copiii din cartier, aproape de casă",
               "părinții și bunicii se întâlnesc; comunitatea se cunoaște",
               "reduce deplasările cu mașina către parcurile mari"],
    riscuri_specifice=["echipamentele de joacă trebuie să aibă certificare de conformitate (standardul european "
                       "pentru echipamente de joacă, SR EN 1176), verificată de furnizor",
                       "zona amortizoare din jurul echipamentelor se verifică la proiectare"],
    ipoteze=["Zonele libere din jurul echipamentelor sunt ipoteze schematice; proiectantul aplică standardul."],
    surse=["cunoștințe generale; SR EN 1176 (echipamente pentru spații de joacă) ca referință de conformitate, "
           "nu ca dimensiune preluată"],
))

_add(Specificatie(
    tip_amenajare="parc_caini", eticheta="parc pentru câini", suprafata_minima_mp=200, suprafata_recomandata_mp=600,
    utilitati_necesare=[APA], categorie_lucrare=["amenajare_exterioara", "instalatie_apa"],
    componente=[
        C(nume="zonă de alergare și agility", categorie="echipament", latime_m=12, lungime_m=8, min_latime_m=6,
          min_lungime_m=5, inaltime_m=1.0, zona_libera_m=0.5, obligatoriu=True,
          rol="teren îngrădit cu obstacole de agility", tip_desen="caini", articol="amenajare_caini"),
        C(nume="zonă separată pentru câini mici", categorie="echipament", latime_m=8, lungime_m=6, min_latime_m=4,
          min_lungime_m=4, inaltime_m=1.0, zona_libera_m=0.5, rol="separare pe talie", tip_desen="caini",
          articol="amenajare_caini"),
        C(nume="adăpătoare", categorie="instalatie", latime_m=1, lungime_m=1, inaltime_m=0.8, zona_libera_m=0.5,
          rol="apă pentru animale și stăpâni", utilitati=[APA], articol="cismea", tip_desen="apa"),
        C(nume="dozator de pungi", categorie="mobilier", cantitate=2, latime_m=0.5, lungime_m=0.5, inaltime_m=1.2,
          zona_libera_m=0.3, rol="curățenie", tip_desen="cos"),
        C(nume="gard dublu cu sas la intrare", categorie="siguranta", unitate="ml", pe_plan=False,
          derivat_din="plan_perimetru", rol="împrejmuire înaltă, cu zonă tampon la intrare", articol="gard"),
        _BANCI, _COSURI, _PANOU, _ALEE, _GAZON,
    ],
    beneficii=["câinii sunt plimbați liber într-un loc îngrădit, nu printre blocuri",
               "mai puține conflicte între proprietarii de câini și ceilalți locuitori",
               "comunitate de stăpâni care se cunosc"],
    riscuri_specifice=["întreținerea curățeniei depinde de administrator și de utilizatori",
                       "lătratul: distanța față de ferestre trebuie evaluată"],
    ipoteze=["Dimensiunile zonelor sunt schematice."], surse=["cunoștințe generale despre parcuri canine publice"],
))

_add(Specificatie(
    tip_amenajare="pista_biciclete", eticheta="pistă de biciclete", suprafata_minima_mp=150,
    suprafata_recomandata_mp=500, utilitati_necesare=[], categorie_lucrare=["amenajare_exterioara", "platforma"],
    componente=[
        C(nume="pistă de biciclete în buclă", categorie="finisaj", unitate="mp", pe_plan=False,
          derivat_din="plan_element", obligatoriu=True, rol="buclă asfaltată de 2,5 m lățime pe conturul terenului",
          tip_desen="pista", articol="imbracaminte_pista"),
        C(nume="rastel pentru biciclete", categorie="mobilier", latime_m=3, lungime_m=1, inaltime_m=0.9,
          zona_libera_m=0.5, rol="parcare biciclete", articol="rastel_biciclete", tip_desen="rastel"),
        C(nume="zonă de învățare pentru copii", categorie="echipament", latime_m=8, lungime_m=6, min_latime_m=5,
          min_lungime_m=4, inaltime_m=0.1, zona_libera_m=0.5, rol="platformă cu marcaje de circulație",
          tip_desen="pista", articol="imbracaminte_pista"),
        C(nume="marcaje și indicatoare rutiere didactice", categorie="semnalizare", cantitate=1, unitate="set",
          pe_plan=False, rol="educație rutieră"),
        _BANCI, _COSURI, _PANOU, _GAZON,
    ],
    beneficii=["copiii învață să circule pe bicicletă în siguranță", "mișcare pentru toate vârstele"],
    riscuri_specifice=["asfaltul se degradează fără întreținere; nevoia de marcaje reîmprospătate"],
    ipoteze=["Pista e o buclă de 2,5 m lățime pe conturul terenului (ipoteză schematică)."],
    surse=["cunoștințe generale"],
))

_add(Specificatie(
    tip_amenajare="gradina_comunitara", eticheta="grădină comunitară", suprafata_minima_mp=100,
    suprafata_recomandata_mp=400, utilitati_necesare=[APA], categorie_lucrare=["amenajare_exterioara", "instalatie_apa"],
    componente=[
        C(nume="strat înălțat", categorie="constructie", cantitate=10, latime_m=3, lungime_m=1.2, inaltime_m=0.6,
          zona_libera_m=0.6, obligatoriu=True, rol="parcele de cultivat, repartizate familiilor",
          tip_desen="strat", articol="strat_inaltat"),
        C(nume="magazie de unelte", categorie="constructie", latime_m=2.5, lungime_m=2, inaltime_m=2.2,
          zona_libera_m=0.5, rol="depozitare unelte și semințe", tip_desen="magazie"),
        C(nume="zonă de compost", categorie="echipament", latime_m=2, lungime_m=1.5, inaltime_m=1.0,
          zona_libera_m=0.5, rol="compostarea resturilor vegetale", articol="compostor", tip_desen="compost"),
        C(nume="rezervor de apă și punct de udare", categorie="instalatie", latime_m=1, lungime_m=1, inaltime_m=1.5,
          zona_libera_m=0.3, rol="irigare", utilitati=[APA], articol="cismea", tip_desen="apa"),
        _BANCI, _COSURI, _PANOU, _ALEE, _GARD, _GAZON,
    ],
    beneficii=["legume și flori crescute de vecini; educație pentru copii",
               "întâlniri între generații; întreținerea e făcută de comunitate"],
    riscuri_specifice=["solul poate necesita analiză (foste zone industriale)", "accesul la apă e esențial"],
    ipoteze=["Numărul de straturi se adaptează la suprafață."], surse=["cunoștințe generale"],
))

_add(Specificatie(
    tip_amenajare="teren_sport", eticheta="teren de sport", suprafata_minima_mp=300, suprafata_recomandata_mp=800,
    utilitati_necesare=[ENERGIE], categorie_lucrare=["amenajare_exterioara", "platforma", "iluminat"],
    componente=[
        C(nume="teren multisport (minifotbal, baschet, handbal)", categorie="echipament", latime_m=30, lungime_m=15,
          min_latime_m=15, min_lungime_m=11, inaltime_m=0.1, zona_libera_m=1.0, obligatoriu=True,
          rol="suprafață sintetică cu marcaje și porți/panouri", tip_desen="sport", articol="suprafata_sport"),
        C(nume="plasă de protecție perimetrală", categorie="siguranta", unitate="ml", pe_plan=False,
          derivat_din="plan_perimetru", rol="oprirea mingilor, înălțime 4 m", articol="gard"),
        C(nume="porți și panouri de baschet", categorie="echipament", cantitate=1, unitate="set", pe_plan=False,
          rol="echipament sportiv fix"),
        C(nume="stâlp de iluminat LED", categorie="instalatie", cantitate=4, latime_m=0.3, lungime_m=0.3,
          inaltime_m=8.0, zona_libera_m=0.3, rol="nocturnă", utilitati=[ENERGIE], articol="stalp_iluminat",
          tip_desen="iluminat"),
        _BANCI, _COSURI, _PANOU, _ALEE, _GAZON,
    ],
    beneficii=["sport gratuit pentru tineri și adulți", "echipe de cartier, turnee locale"],
    riscuri_specifice=["zgomot seara; programul de iluminat trebuie limitat"],
    ipoteze=["Dimensiunile terenului sunt schematice (sub cele ale unui teren oficial)."],
    surse=["cunoștințe generale"],
))

_add(Specificatie(
    tip_amenajare="foisor", eticheta="foișor", suprafata_minima_mp=40, suprafata_recomandata_mp=150,
    utilitati_necesare=[], categorie_lucrare=["constructie_usoara"],
    componente=[
        C(nume="foișor", categorie="constructie", latime_m=5, lungime_m=5, min_latime_m=4, min_lungime_m=4,
          inaltime_m=3.2, zona_libera_m=1.0, obligatoriu=True, rol="structură acoperită din lemn, deschisă",
          articol="foisor", tip_desen="foisor"),
        C(nume="masă cu bănci", categorie="mobilier", cantitate=2, latime_m=2, lungime_m=1.8, inaltime_m=0.8,
          zona_libera_m=0.6, rol="mese de picnic", articol="masa_picnic", tip_desen="masa"),
        _BANCI, _COSURI, _ALEE, _GAZON,
    ],
    beneficii=["loc de întâlnire la umbră pentru vecini și vârstnici", "evenimente mici de cartier"],
    riscuri_specifice=["lemnul cere tratare și întreținere periodică"],
    ipoteze=["Foișorul e o construcție ușoară; încadrarea juridică exactă o dă certificatul de urbanism."],
    surse=["cunoștințe generale"],
))

_add(Specificatie(
    tip_amenajare="statie_incarcare", eticheta="stație de încărcare pentru vehicule electrice",
    suprafata_minima_mp=30, suprafata_recomandata_mp=80, utilitati_necesare=[ENERGIE],
    categorie_lucrare=["instalatie_electrica", "parcare", "semnalizare"],
    componente=[
        C(nume="loc de parcare dedicat încărcării", categorie="terasament", cantitate=25, unitate="mp", latime_m=2.5,
          lungime_m=5, inaltime_m=0.0, zona_libera_m=0.0, obligatoriu=True, bucati_plan=2,
          rol="două platforme marcate de 2,5 × 5 m, câte una per priză", tip_desen="parcare", articol="pavaj",
          derivat_din="plan_element"),
        C(nume="punct de încărcare AC 22 kW (dublu, tip 2)", categorie="echipament", cantitate=1, latime_m=0.4,
          lungime_m=0.3, inaltime_m=1.5, zona_libera_m=0.5, obligatoriu=True,
          rol="încărcător cu două prize, între cele două locuri de parcare", utilitati=[ENERGIE],
          articol="statie_incarcare_ac", tip_desen="echipament"),
        C(nume="tablou electric de distribuție și protecții", categorie="instalatie", cantitate=1, latime_m=0.8,
          lungime_m=0.4, inaltime_m=1.6, zona_libera_m=0.5, obligatoriu=True,
          rol="siguranțe, protecție diferențială, contor", utilitati=[ENERGIE], articol="tablou_electric",
          tip_desen="echipament"),
        C(nume="branșament electric (racord la rețeaua de distribuție)", categorie="instalatie", cantitate=1,
          unitate="set", pe_plan=False, obligatoriu=True, rol="aviz tehnic de racordare și lucrarea de racord, prin "
          "operatorul de distribuție", utilitati=[ENERGIE], articol="bransament_electric"),
        C(nume="cablu de alimentare îngropat (tub de protecție)", categorie="instalatie", cantitate=25, unitate="ml",
          pe_plan=False, rol="de la tablou la punctul de încărcare și la racord", articol="cablu_electric"),
        C(nume="sistem de plată și gestiune (OCPP, card/aplicație)", categorie="servicii", cantitate=1, unitate="set",
          pe_plan=False, rol="autorizare, tarifare, monitorizare la distanță"),
        C(nume="borne de protecție", categorie="siguranta", cantitate=2, latime_m=0.2, lungime_m=0.2,
          inaltime_m=0.8, zona_libera_m=0.1, rol="protejează încărcătorul de lovituri", tip_desen="siguranta",
          articol="borna_protectie"),
        C(nume="marcaj rutier și indicator „loc rezervat încărcării”", categorie="semnalizare", cantitate=1,
          unitate="set", pe_plan=False, rol="semnalizare conform regulilor de circulație"),
        C(nume="stâlp de iluminat LED", categorie="instalatie", cantitate=1, latime_m=0.3, lungime_m=0.3,
          inaltime_m=4.0, zona_libera_m=0.3, rol="vizibilitate și siguranță noaptea", utilitati=[ENERGIE],
          articol="stalp_iluminat", tip_desen="iluminat"),
    ],
    beneficii=["locuitorii fără garaj pot avea mașină electrică", "mai puțin zgomot și noxe în cartier",
               "poate fi finanțată prin programe publice (AFM) sau operată de un furnizor privat"],
    riscuri_specifice=["puterea disponibilă în rețea decide dacă racordul e simplu sau costisitor",
                       "vandalism și ocuparea locurilor de mașini care nu încarcă"],
    ipoteze=["Puterea de 22 kW AC e o alegere tipică pentru încărcare lentă rezidențială; proiectul tehnic și "
             "avizul de racordare stabilesc puterea reală.",
             "Nu se prevede gazon sau pardoseală de cauciuc: stația e o platformă carosabilă."],
    surse=["Ghidul AFM pentru stații de reîncărcare (Ordin 1962/2021) ca referință de program; cunoștințe generale "
           "despre instalații electrice"],
))

_add(Specificatie(
    tip_amenajare="fantana_publica", eticheta="fântână publică de băut apă (cișmea)", suprafata_minima_mp=6,
    suprafata_recomandata_mp=20, utilitati_necesare=[APA, CANAL],
    categorie_lucrare=["instalatie_apa", "canalizare", "amenajare_exterioara"],
    componente=[
        C(nume="cișmea publică din metal, cu buton temporizat", categorie="echipament", cantitate=1, latime_m=0.5,
          lungime_m=0.5, inaltime_m=1.0, zona_libera_m=0.8, obligatoriu=True,
          rol="apă potabilă pentru trecători; variantă cu robinet jos pentru animale", utilitati=[APA, CANAL],
          articol="cismea", tip_desen="apa"),
        C(nume="racord la rețeaua de apă potabilă", categorie="instalatie", cantitate=1, unitate="set", pe_plan=False,
          obligatoriu=True, rol="branșament cu contor, prin operatorul de apă-canal", utilitati=[APA],
          articol="bransament_apa"),
        C(nume="racord la canalizare / rigolă de scurgere", categorie="instalatie", cantitate=1, unitate="set",
          pe_plan=False, obligatoriu=True, rol="evacuarea apei scurse", utilitati=[CANAL], articol="bransament_canal"),
        C(nume="conductă de apă îngropată (sub adâncimea de îngheț)", categorie="instalatie", cantitate=15,
          unitate="ml", pe_plan=False, rol="de la branșament la cișmea", articol="conducta_apa"),
        C(nume="platformă pavată antiderapantă", categorie="finisaj", unitate="mp", pe_plan=False,
          derivat_din="plan_zona_libera", rol="zona din jurul cișmelei, cu pantă spre rigolă", articol="pavaj"),
        C(nume="cămin de vane cu robinet de golire pentru iarnă", categorie="instalatie", cantitate=1, latime_m=0.6,
          lungime_m=0.6, inaltime_m=0.0, zona_libera_m=0.2, rol="golirea instalației în sezonul rece",
          tip_desen="apa"),
        _COSURI,
    ],
    beneficii=["apă potabilă gratuită pentru pietoni, copii, sportivi și animale",
               "mai puține sticle de plastic", "răcorire în zilele caniculare"],
    riscuri_specifice=["calitatea apei trebuie confirmată de operator și de Direcția de Sănătate Publică",
                       "instalația se golește iarna; altfel îngheață"],
    ipoteze=["Lungimea conductei (15 m) e o ipoteză; depinde de distanța până la rețea."],
    surse=["cunoștințe generale despre cișmele publice"],
))

_add(Specificatie(
    tip_amenajare="aquapark", eticheta="parc acvatic", suprafata_minima_mp=3000, suprafata_recomandata_mp=10000,
    utilitati_necesare=[APA, CANAL, ENERGIE],
    categorie_lucrare=["constructie", "bazine", "instalatie_apa", "canalizare", "instalatie_electrica", "parcare"],
    componente=[
        C(nume="bazin principal", categorie="constructie", latime_m=25, lungime_m=12, min_latime_m=20,
          min_lungime_m=10, inaltime_m=1.8, zona_libera_m=2.0, obligatoriu=True,
          rol="bazin de înot/agrement, cu plajă perimetrală", tip_desen="apa", articol="bazin"),
        C(nume="bazin pentru copii", categorie="constructie", latime_m=8, lungime_m=6, inaltime_m=0.5,
          zona_libera_m=2.0, obligatoriu=True, rol="adâncime mică", tip_desen="apa", articol="bazin"),
        C(nume="turn cu tobogane acvatice", categorie="echipament", latime_m=10, lungime_m=8, inaltime_m=8.0,
          zona_libera_m=2.0, rol="2-3 tobogane cu bazin de recepție", tip_desen="echipament"),
        C(nume="vestiare, dușuri și grupuri sanitare", categorie="constructie", latime_m=12, lungime_m=6,
          inaltime_m=3.5, zona_libera_m=1.0, obligatoriu=True, rol="clădire cu acces pentru persoane cu dizabilități",
          utilitati=[APA, CANAL, ENERGIE], tip_desen="cladire"),
        C(nume="stație de pompe și tratare a apei (filtrare, clorinare)", categorie="instalatie", latime_m=6,
          lungime_m=4, inaltime_m=3.0, zona_libera_m=1.0, obligatoriu=True, rol="recircularea și tratarea apei",
          utilitati=[APA, CANAL, ENERGIE], tip_desen="cladire"),
        C(nume="punct de prim ajutor și post de salvamar", categorie="siguranta", latime_m=3, lungime_m=3,
          inaltime_m=3.0, zona_libera_m=0.5, obligatoriu=True, rol="supraveghere și intervenție", tip_desen="cladire"),
        C(nume="racorduri la apă, canalizare și energie", categorie="instalatie", cantitate=1, unitate="set",
          pe_plan=False, obligatoriu=True, rol="branșamente dimensionate pentru debitele bazinelor",
          utilitati=[APA, CANAL, ENERGIE]),
        C(nume="parcare", categorie="terasament", latime_m=30, lungime_m=15, inaltime_m=0.0, zona_libera_m=0.5,
          rol="circa 30 de locuri", tip_desen="parcare", articol="pavaj", derivat_din="plan_element"),
        _ILUMINAT, _BANCI, _COSURI, _ALEE, _GARD, _GAZON,
    ],
    beneficii=["agrement de vară în oraș; mai puține deplasări către ștranduri îndepărtate",
               "locuri de muncă sezoniere"],
    riscuri_specifice=["investiție și costuri de operare mari (apă, energie, personal); de obicei proiect al "
                       "Primăriei sau în parteneriat, nu amenajare de cartier",
                       "consum mare de apă; avize sanitare și de mediu complexe"],
    ipoteze=["Suprafața minimă de 3.000 mp e o ipoteză a aplicației pentru un parc acvatic mic."],
    surse=["cunoștințe generale despre ștranduri și parcuri acvatice publice"],
))

ALIASES_EXTRA: list[tuple[str, str]] = [
    (r"statie|stati(a|i) de (re)?incarcare|incarcator|masini electrice|vehicule electrice|\bev\b", "statie_incarcare"),
    (r"cismea|fantana (publica|de baut|cu apa potabila)|apa potabila|fantana arteziana|\bfantana\b", "fantana_publica"),
    (r"aquapark|aqua park|parc acvatic|strand|piscina", "aquapark"),
]
