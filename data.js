// Liste de clients par défaut (nom + email destinataire).
// Éditable depuis l'interface ; persistée en localStorage.
window.CLIENTS_SEED = [
  { id: "c1", name: "Renault — Cléon", email: "ops.cleon@renault.example" },
  { id: "c2", name: "Safran — Villaroche", email: "formation@safran.example" },
  { id: "c3", name: "Michelin — Clermont", email: "team-ops@michelin.example" },
  { id: "c4", name: "Schneider — Grenoble", email: "ops@se.example" },
];

// Catalogue d'articles — structure miroir du dossier « video helpdesk - V1 »
// (catégorie -> section -> article). Chaque article a une vidéo ; le PDF
// correspondant (dossier « Articles Helpdesk … ») est rattaché quand il existe.
window.CATALOG = [
  {
    "id": "par",
    "name": "Paramètres",
    "icon": "⚙️",
    "desc": "Connexion, usine, comptes, imports et règles de calcul.",
    "exercises": [
      {
        "id": "par1",
        "title": "Comment se connecter à Oplit",
        "section": "I - Connexion",
        "min": 1,
        "video": "video helpdesk - V1/Paramètres/I - Connexion/Comment se connecter à Oplit.mp4",
        "pdf": "Articles Helpdesk pour alimentation IA/Paramètres/I - Connexion/Comment se connecter à Oplit _ FAQ Oplit.pdf",
        "drive": "https://drive.google.com/file/d/1ff5QOodEQDQhEP-ntEEnt7ABWr7oEZWp/view",
        "dur": 63
      }
    ]
  },
  {
    "id": "pla",
    "name": "Planification",
    "icon": "📅",
    "desc": "Gestion de l'usine, simulations PDP, événements et vues.",
    "exercises": [
      {
        "id": "pla1",
        "title": "Comparer sa simulation à une autre - PDP",
        "section": "IV - Navigation de mes différentes vues",
        "min": 1,
        "video": "video helpdesk - V1/Planification/IV - Navigation de mes différentes vues/Comparer sa simulation à une autre - PDP.mp4",
        "pdf": "Articles Helpdesk pour alimentation IA/Planification/IV - Navigation de mes différentes vues/Comparer sa simulation à une autre - PDP _ FAQ Oplit.pdf",
        "drive": "https://drive.google.com/file/d/1MqukO29LUiUK8fMpyNbYKRQFh63EkDmr/view",
        "dur": 63
      },
      {
        "id": "pla2",
        "title": "Créer un event dans onglet Charge",
        "section": "V - Création et gestion de mes événements",
        "min": 2,
        "video": "video helpdesk - V1/Planification/V - Création et gestion de mes événements/Créer un event dans onglet _Charge_.mp4",
        "pdf": "Articles Helpdesk pour alimentation IA/Planification/V - Création et gestion de mes événements/Créer un event dans onglet _Charge_ _ FAQ Oplit.pdf",
        "drive": "https://drive.google.com/file/d/1l3dC0iJZuF5cRu_qGl8NPZ71TFTuodeT/view",
        "dur": 134
      }
    ]
  },
  {
    "id": "ord",
    "name": "Ordonnancement",
    "icon": "🧩",
    "desc": "Paramétrage, planification auto et exploitation du module ordo.",
    "exercises": [
      {
        "id": "ord1",
        "title": "Gérer ma capacité journalière - Ordo",
        "section": "I - Gestion de mon usine (planning et machine)",
        "min": 1,
        "video": "video helpdesk - V1/Ordonnancement/I - Gestion de mon usine (planning et machine)/Gérer ma capacité journalière - Ordo.mp4",
        "pdf": "Articles Helpdesk pour alimentation IA/Ordonnancement/I - Gestion de mon usine (planning et machine)/Gérer ma capacité journalière - Ordo _ FAQ Oplit.pdf",
        "drive": "https://drive.google.com/file/d/12vIsmV-qfpgLe9iMNUGjrqFN-D7eRWnG/view",
        "dur": 61
      },
      {
        "id": "ord2",
        "title": "Comment gérer mon filtre",
        "section": "IV - Gestion de l_affichage et des filtres en ordonnancement",
        "min": 1,
        "video": "video helpdesk - V1/Ordonnancement/IV - Gestion de l_affichage et des filtres en ordonnancement/Comment gérer mon filtre.mp4",
        "pdf": "Articles Helpdesk pour alimentation IA/Ordonnancement/IV - Gestion de l_affichage et des filtres en ordonnancement/Comment gérer mon filtre _ FAQ Oplit.pdf",
        "drive": "https://drive.google.com/file/d/1yjfYf-NKoZzM-_vyN_cNOzm_6gr9p3jk/view",
        "dur": 56
      }
    ]
  },
  {
    "id": "sto",
    "name": "Stock",
    "icon": "📦",
    "desc": "Paramétrage et navigation du module Stock.",
    "exercises": [
      {
        "id": "sto1",
        "title": "Principe du module Stock",
        "section": "0 - Préambule",
        "min": 1,
        "video": "video helpdesk - V1/Stock/0 - Préambule/Principe du module Stock.mp4",
        "pdf": "Articles Helpdesk pour alimentation IA/Stock/0 - Préambule/Principe du module Stock _ FAQ Oplit.pdf",
        "drive": "https://drive.google.com/file/d/1UuXLV-nPtVAQIFKVR13XfTUvlX6Domh9/view",
        "dur": 46
      },
      {
        "id": "sto2",
        "title": "Créer et modifier la liste des opérateurs - Stock",
        "section": "I - Gestion de mon usine (planning et machine)",
        "min": 1,
        "video": "video helpdesk - V1/Stock/I - Gestion de mon usine (planning et machine)/Créer et modifier la liste des opérateurs - Stock.mp4",
        "pdf": "Articles Helpdesk pour alimentation IA/Stock/I - Gestion de mon usine (planning et machine)/Créer et modifier la liste des opérateurs - Stock _ FAQ Oplit.pdf",
        "drive": "https://drive.google.com/file/d/1l8G99KmJ6JAOcN1ISvfNChRnzfbRrFVN/view",
        "dur": 52
      },
      {
        "id": "sto3",
        "title": "Créer et modifier les machines - Stock",
        "section": "I - Gestion de mon usine (planning et machine)",
        "min": 1,
        "video": "video helpdesk - V1/Stock/I - Gestion de mon usine (planning et machine)/Créer et modifier les machines - Stock.mp4",
        "pdf": "Articles Helpdesk pour alimentation IA/Stock/I - Gestion de mon usine (planning et machine)/Créer et modifier les machines - Stock _ FAQ Oplit.pdf",
        "drive": "https://drive.google.com/file/d/1G9I982Lzuu685FeTA_N_Zml6sHAguADc/view",
        "dur": 37
      },
      {
        "id": "sto4",
        "title": "Créer le planning standard de mes postes de charge - Stock",
        "section": "I - Gestion de mon usine (planning et machine)",
        "min": 1,
        "video": "video helpdesk - V1/Stock/I - Gestion de mon usine (planning et machine)/Créer le planning standard de mes postes de charge - Stock.mp4",
        "pdf": "Articles Helpdesk pour alimentation IA/Stock/I - Gestion de mon usine (planning et machine)/Créer le planning standard de mes postes de charge - Stock _ FAQ Oplit.pdf",
        "drive": "https://drive.google.com/file/d/1Sye5GW2TE5dYbRuqXVntbaRwpAUn-aq5/view",
        "dur": 74
      },
      {
        "id": "sto5",
        "title": "Définir le calendrier d ouverture de mon usine - Stock",
        "section": "I - Gestion de mon usine (planning et machine)",
        "min": 1,
        "video": "video helpdesk - V1/Stock/I - Gestion de mon usine (planning et machine)/Définir le calendrier d_ouverture de mon usine - Stock.mp4",
        "pdf": "Articles Helpdesk pour alimentation IA/Stock/I - Gestion de mon usine (planning et machine)/Définir le calendrier d_ouverture de mon usine - Stock _ FAQ Oplit.pdf",
        "drive": "https://drive.google.com/file/d/1kYuMC8nWxel_TpzgH5Du_J56IXirel0E/view",
        "dur": 55
      },
      {
        "id": "sto6",
        "title": "Modifier la structure de mon usine - Stock",
        "section": "I - Gestion de mon usine (planning et machine)",
        "min": 2,
        "video": "video helpdesk - V1/Stock/I - Gestion de mon usine (planning et machine)/Modifier la structure de mon usine - Stock.mp4",
        "pdf": "Articles Helpdesk pour alimentation IA/Stock/I - Gestion de mon usine (planning et machine)/Modifier la structure de mon usine - Stock _ FAQ Oplit.pdf",
        "drive": "https://drive.google.com/file/d/1gCeB8kvz-15oHBtiF7aJkYu74QIs4bOS/view",
        "dur": 105
      },
      {
        "id": "sto7",
        "title": "Affecter les règles de calcul de la capacité aux secteurs",
        "section": "II - Gestion des règles de calcul de la capacité",
        "min": 1,
        "video": "video helpdesk - V1/Stock/II - Gestion des règles de calcul de la capacité/Affecter les règles de calcul de la capacité aux secteurs.mp4",
        "pdf": "Articles Helpdesk pour alimentation IA/Stock/II - Gestion des règles de calcul de la capacité/Affecter les règles de calcul de la capacité aux secteurs _ FAQ Oplit.pdf",
        "drive": "https://drive.google.com/file/d/1IC_lz_7WBY3s6xljMzBn8xzdZuyA6wh3/view",
        "dur": 83
      },
      {
        "id": "sto8",
        "title": "Définir les règles de calcul de la capacité - Stock",
        "section": "II - Gestion des règles de calcul de la capacité",
        "min": 1,
        "video": "video helpdesk - V1/Stock/II - Gestion des règles de calcul de la capacité/Définir les règles de calcul de la capacité - Stock.mp4",
        "pdf": "Articles Helpdesk pour alimentation IA/Stock/II - Gestion des règles de calcul de la capacité/Définir les règles de calcul de la capacité - Stock _ FAQ Oplit.pdf",
        "drive": "https://drive.google.com/file/d/1Ti5Xlzq0mptygvRni6TFAiyVDhUT3K3J/view",
        "dur": 45
      },
      {
        "id": "sto9",
        "title": "Comment paramétrer la gamme de fabrication de mon module Stock",
        "section": "III - Paramétrage du module stock",
        "min": 1,
        "video": "video helpdesk - V1/Stock/III - Paramétrage du module stock/Comment paramétrer la gamme de fabrication de mon module Stock.mp4",
        "pdf": "Articles Helpdesk pour alimentation IA/Stock/III - Paramétrage du module stock/Comment paramétrer la gamme de fabrication de mon module Stock _ FAQ Oplit.pdf",
        "drive": "https://drive.google.com/file/d/1cqJvNBSDgucoecFvfks6h7QqTxDJxwsR/view",
        "dur": 78
      },
      {
        "id": "sto10",
        "title": "Comment paramétrer la nomenclature de mon module Stock",
        "section": "III - Paramétrage du module stock",
        "min": 1,
        "video": "video helpdesk - V1/Stock/III - Paramétrage du module stock/Comment paramétrer la nomenclature de mon module Stock.mp4",
        "pdf": "Articles Helpdesk pour alimentation IA/Stock/III - Paramétrage du module stock/Comment paramétrer la nomenclature de mon module Stock _ FAQ Oplit.pdf",
        "drive": "https://drive.google.com/file/d/1Rwn2-jhFYRdeWOcj1mTpujkGsq9VpfID/view",
        "dur": 73
      },
      {
        "id": "sto11",
        "title": "Import des données - Stocks",
        "section": "III - Paramétrage du module stock",
        "min": 2,
        "video": "video helpdesk - V1/Stock/III - Paramétrage du module stock/Import des données - Stocks.mp4",
        "pdf": "Articles Helpdesk pour alimentation IA/Stock/III - Paramétrage du module stock/Import des données - Stocks _ FAQ Oplit.pdf",
        "drive": "https://drive.google.com/file/d/12qctGdD2j_KfnK_6OfHFnV40JBKX-qwt/view",
        "dur": 109
      },
      {
        "id": "sto12",
        "title": "Comment se servir de l onglet Demande",
        "section": "IV - Navigation dans mes différentes vues",
        "min": 1,
        "video": "video helpdesk - V1/Stock/IV - Navigation dans mes différentes vues/Comment se servir de l_onglet Demande.mp4",
        "pdf": "Articles Helpdesk pour alimentation IA/Stock/IV - Navigation dans mes différentes vues/Comment se servir de l_onglet Demande _ FAQ Oplit.pdf",
        "drive": "https://drive.google.com/file/d/1XI9a0mp2DXnlvCg2aq97OWsNG757KGqH/view",
        "dur": 83
      },
      {
        "id": "sto13",
        "title": "Comment se servir de l onglet Fabrication",
        "section": "IV - Navigation dans mes différentes vues",
        "min": 1,
        "video": "video helpdesk - V1/Stock/IV - Navigation dans mes différentes vues/Comment se servir de l_onglet Fabrication.mp4",
        "pdf": "Articles Helpdesk pour alimentation IA/Stock/IV - Navigation dans mes différentes vues/Comment se servir de l_onglet Fabrication _ FAQ Oplit.pdf",
        "drive": "https://drive.google.com/file/d/12zbogMtScauBF34kEUwpu3rwwRyn_MD7/view",
        "dur": 80
      },
      {
        "id": "sto14",
        "title": "Comment se servir de l onglet Stock",
        "section": "IV - Navigation dans mes différentes vues",
        "min": 1,
        "video": "video helpdesk - V1/Stock/IV - Navigation dans mes différentes vues/Comment se servir de l_onglet Stock.mp4",
        "pdf": "Articles Helpdesk pour alimentation IA/Stock/IV - Navigation dans mes différentes vues/Comment se servir de l_onglet Stock _ FAQ Oplit.pdf",
        "drive": "https://drive.google.com/file/d/1kJwsZZAWS1ZtzgzY8qIFf9sXTCmlGwB7/view",
        "dur": 78
      },
      {
        "id": "sto15",
        "title": "Visualisation de l évolution des stocks",
        "section": "IV - Navigation dans mes différentes vues",
        "min": 1,
        "video": "video helpdesk - V1/Stock/IV - Navigation dans mes différentes vues/Visualisation de l_évolution des stocks.mp4",
        "pdf": "Articles Helpdesk pour alimentation IA/Stock/IV - Navigation dans mes différentes vues/Visualisation de l_évolution des stocks _ FAQ Oplit.pdf",
        "drive": "https://drive.google.com/file/d/1GXCNczFNoX0GxXKkklG1McNKHXykQwjn/view",
        "dur": 58
      }
    ]
  },
  {
    "id": "cli",
    "name": "Client-fournisseur",
    "icon": "🤝",
    "desc": "Paramétrage de l'interface de suivi fournisseur.",
    "exercises": [
      {
        "id": "cli1",
        "title": "Comment paramétrer l interface Suivi fournisseur",
        "section": "",
        "min": 2,
        "video": "video helpdesk - V1/Client-fournisseur/Comment paramétrer l_interface Suivi fournisseur.mp4",
        "pdf": "Articles Helpdesk pour alimentation IA/Client-fournisseur/Comment paramétrer l_interface Suivi fournisseur _ FAQ Oplit.pdf",
        "drive": "https://drive.google.com/file/d/1z8anrxKO4JMwK-erPaavtwMLK0hIci6x/view",
        "dur": 99
      }
    ]
  }
];
