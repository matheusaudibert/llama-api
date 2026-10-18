# Copied verbatim from bot.py

rarity_priority = {
    "Mythic": 1,
    "Legendary": 2,
    "DARK SERIES": 3,
    "Slurp Series": 4,
    "Star Wars Series": 5,
    "MARVEL SERIES": 6,
    "Lava Series": 7,
    "Frozen Series": 8,
    "Gaming Legends Series": 9,
    "Shadow Series": 10,
    "Icon Series": 11,
    "DC SERIES": 12,
    "Epic": 13,
    "Rare": 14,
    "Uncommon": 15,
    "Common": 16
}

sub_order = {
    "cid_017_athena_commando_m": 1,
    "cid_028_athena_commando_f": 2,
    "cid_029_athena_commando_f_halloween": 3,
    "cid_030_athena_commando_m_halloween": 4,
    "cid_035_athena_commando_m_medieval": 5,
    "cid_313_athena_commando_m_kpopfashion": 6,
    "cid_757_athena_commando_f_wildcat": 7,
    "cid_039_athena_commando_f_disco": 8,
    "cid_033_athena_commando_f_medieval": 9,
    "cid_032_athena_commando_m_medieval": 10,
    "cid_084_athena_commando_m_assassin": 11,
    "cid_095_athena_commando_m_founder": 12,
    "cid_096_athena_commando_f_founder": 13,
    "cid_113_athena_commando_m_blueace": 14,
    "cid_116_athena_commando_m_carbideblack": 15,
    "cid_175_athena_commando_m_celestial": 16,
    "cid_183_athena_commando_m_modernmilitaryred": 17,
    "cid_342_athena_commando_m_streetracermetallic": 18,
    "cid_371_athena_commando_m_speedymidnight": 19,
    "cid_434_athena_commando_f_stealthhonor": 20,
    "cid_441_athena_commando_f_cyberscavengerblue": 21,
    "cid_479_athena_commando_f_davinci": 22,
    "cid_515_athena_commando_m_barbequelarry": 23,
    "cid_516_athena_commando_m_blackwidowrogue": 24,
    "cid_703_athena_commando_m_cyclone": 25,
    "cid_npc_athena_commando_m_masterkey": 26
}


mythic_ids = [
    "cid_017_athena_commando_m", "cid_028_athena_commando_f", "eid_tidy", "banner_influencerbanner21", "banner_brseason01", "banner_ot1banner", "banner_ot2banner", "banner_ot3banner", "banner_ot4banner", "banner_ot5banner",
    "banner_influencerbanner54", "banner_influencerbanner38", "banner_ot6banner", "banner_ot7banner", "banner_ot8banner", "banner_ot9banner", "banner_ot10banner", "banner_ot11banner",
    "cid_032_athena_commando_m_medieval", "cid_033_athena_commando_f_medieval", "cid_035_athena_commando_m_medieval",
    "eid_uproar_496sc", "eid_textile_3o8qg", "eid_sunrise_rpz6m", "eid_sleek_s20cu", "eid_sandwichbop", "eid_sahara", "eid_rigormortis", "eid_richfam", "eid_provisitorprotest", "eid_playereleven", "eid_lasagnadance", "eid_jingle", "eid_hoppin", "eid_hnygoodriddance", "eid_hawtchamp", "eid_gleam", "eid_galileo3_t4dko", "eid_eerie_8wgyk", "eid_dumbbell_lift", "eid_downward_8gzua", "eid_cyclone", "eid_cycloneheadbang", "eid_astray", "eid_antivisitorprotest", 
    "pickaxe_spookyneonred", "pickaxe_id_tbd_crystalshard", "pickaxe_id_461_skullbritecube", "pickaxe_id_398_wildcatfemale", "pickaxe_id_338_bandageninjablue1h", "pickaxe_id_178_speedymidnight", "pickaxe_id_099_modernmilitaryred", "pickaxe_id_077_carbidewhite", "pickaxe_id_044_tacticalurbanhammer", "pickaxe_id_039_tacticalblack", "pickaxe_accumulateretro", 
    "character_vampirehunter_galaxy", "character_sahara", "character_reconexpert_fncs", "character_masterkeyorder", 
    "cid_a_329_athena_commando_f_uproar_i5n5z", "cid_a_271_athena_commando_m_fncs_purple", "cid_a_269_athena_commando_f_hastestreet_b563i", "cid_a_256_athena_commando_f_uproarbraids_8iozw", "cid_a_215_athena_commando_f_sunrisecastle_48tiz", "cid_a_216_athena_commando_m_sunrisepalace_bbqy0", "cid_a_208_athena_commando_m_textilepup_c85od", "cid_a_207_athena_commando_m_textileknight_9te8l", "cid_a_206_athena_commando_f_textilesparkle_v8ysa", "cid_a_205_athena_commando_f_textileram_gmrj0", "cid_a_196_athena_commando_f_fncsgreen", "cid_a_189_athena_commando_m_lavish_huu31", "cid_a_139_athena_commando_m_foray_sd8aa", "cid_a_138_athena_commando_f_foray_yqpb0", "cid_a_100_athena_commando_m_downpour_kc39p", "cid_914_athena_commando_f_york_e", "cid_913_athena_commando_f_york_d", "cid_912_athena_commando_f_york_c", "cid_911_athena_commando_f_york_b", "cid_910_athena_commando_f_york", "cid_909_athena_commando_m_york_e", "cid_908_athena_commando_m_york_d", "cid_907_athena_commando_m_york_c", "cid_906_athena_commando_m_york_b", "cid_905_athena_commando_m_york", "cid_753_athena_commando_f_hostile", "cid_547_athena_commando_f_meteorwoman", "cid_424_athena_commando_m_vigilante", "cid_423_athena_commando_f_painter", "cid_376_athena_commando_m_darkshaman", "cid_252_athena_commando_m_muertos", 
    "bid_102_buckles", "bid_103_clawed", "bid_104_yellowzip", "bid_114_modernmilitaryred", "bid_136_muertosmale", "bid_234_speedymidnight", "bid_240_darkshamanmale", "bid_288_cyberscavengerfemaleblue", "bid_346_blackwidowrogue", "bid_452_bandageninjablue", "bid_604_skullbritecube", 
    "glider_id_056_carbidewhite", "glider_id_075_modernmilitaryred", "glider_id_092_streetops", "glider_id_122_valentines", "glider_id_131_speedymidnight", "glider_id_137_streetopsstealth", "glider_plaguewaste",
    "cid_a_256_athena_commando_f_uproarbraids_8iozw", "cid_030_athena_commando_m_halloween", "cid_029_athena_commando_f_halloween", "banner_influencerbanner1",
    "banner_influencerbanner2", "banner_influencerbanner3", "banner_influencerbanner4", "banner_influencerbanner5", "banner_influencerbanner6", "banner_influencerbanner7",
    "banner_influencerbanner8", "banner_influencerbanner9", "banner_influencerbanner10", "banner_influencerbanner11", "banner_influencerbanner12", "banner_influencerbanner13", "banner_influencerbanner14", "banner_influencerbanner15", "banner_influencerbanner16",
    "banner_influencerbanner17", "banner_influencerbanner18", "banner_influencerbanner19", "banner_influencerbanner20", "banner_influencerbanner21", "banner_influencerbanner22",
    "banner_influencerbanner23", "banner_influencerbanner24", "banner_influencerbanner25", "banner_influencerbanner26", "banner_influencerbanner27", "banner_influencerbanner28",
    "banner_influencerbanner29", "banner_influencerbanner30", "banner_influencerbanner31", "banner_influencerbanner32", "banner_influencerbanner33", "banner_influencerbanner34",
    "banner_influencerbanner35", "banner_influencerbanner36", "banner_influencerbanner37", "banner_influencerbanner39", "banner_influencerbanner40", "banner_influencerbanner41", 
    "banner_influencerbanner42", "banner_influencerbanner43", "banner_influencerbanner44", "banner_influencerbanner45", "banner_influencerbanner46", "banner_influencerbanner47", 
    "banner_influencerbanner48", "banner_influencerbanner49", "banner_influencerbanner50", "banner_influencerbanner51", "banner_influencerbanner52", "banner_influencerbanner53",
    "banner_foundertier1banner1", "banner_foundertier1banner2", "banner_foundertier1banner3", "banner_foundertier1banner4", "banner_foundertier2banner1", "banner_foundertier2banner2", 
    "banner_foundertier2banner3", "banner_foundertier2banner4", "banner_foundertier2banner5", "banner_foundertier2banner6", "banner_foundertier3banner1", "banner_foundertier3banner2", 
    "banner_foundertier3banner3", "banner_foundertier3banner4", "banner_foundertier3banner5", "banner_foundertier4banner1", "banner_foundertier4banner2", "banner_foundertier4banner3", 
    "banner_foundertier4banner4", "banner_foundertier4banner5", "banner_foundertier5banner1", "banner_foundertier5banner2", "banner_foundertier5banner3", "banner_foundertier5banner4", "banner_foundertier5banner5",
    "cid_052_athena_commando_f_psblue", "cid_095_athena_commando_m_founder", "cid_096_athena_commando_f_founder", "cid_138_athena_commando_m_psburnou", 
    "cid_260_athena_commando_f_streetops", "cid_315_athena_commando_m_teriyakifish", "cid_399_athena_commando_f_ashtonboardwalk", "cid_619_athena_commando_f_techllama",
    "cid_a_024_athena_commando_f_skirmish_qw2bq", "cid_a_101_athena_commando_m_tacticalwoodlandblue", "cid_a_215_athena_commando_f_sunrisecastle_48tiz",
    "cid_a_216_athena_commando_m_sunrisepalace_bbqy0", "pickaxe_id_stw004_tier_5", "pickaxe_id_stw005_tier_6", "cid_925_athena_commando_f_tapdance",
    "bid_072_vikingmale", "cid_138_athena_commando_m_psburnout", "pickaxe_id_stw001_tier_1", "pickaxe_id_stw002_tier_3", "pickaxe_id_stw003_tier_4",
    "pickaxe_id_stw007_basic", "pickaxe_id_153_roseleader", "pickaxe_id_461_skullbritecube", "glider_id_211_wildcatblue", "glider_id_206_donut",
    "cid_113_athena_commando_m_blueace", "cid_114_athena_commando_f_tacticalwoodland", "cid_175_athena_commando_m_celestial", "cid_089_athena_commando_m_retrogrey",
    "cid_174_athena_commando_f_carbidewhite", "cid_183_athena_commando_m_modernmilitaryred", "cid_207_athena_commando_m_footballdudea", "eid_worm",
    "cid_208_athena_commando_m_footballduded", "cid_209_athena_commando_m_footballdudec", "cid_210_athena_commando_f_footballgirla",
    "cid_211_athena_commando_f_footballgirlb", "cid_212_athena_commando_f_footballgirlc", "cid_238_athena_commando_f_footballgirld", 
    "cid_239_athena_commando_m_footballduded", "cid_240_athena_commando_f_plague", "cid_313_athena_commando_m_kpopfashion", "cid_082_athena_commando_m_scavenger",
    "cid_090_athena_commando_m_tactical", "cid_657_athena_commando_f_techopsblue", "cid_371_athena_commando_m_speedymidnight", "cid_085_athena_commando_m_twitch",
    "cid_342_athena_commando_m_streetracermetallic", "cid_434_athena_commando_f_stealthhonor", "cid_441_athena_commando_f_cyberscavengerblue", "cid_479_athena_commando_f_davinci",
    "cid_478_athena_commando_f_worldcup", "cid_515_athena_commando_m_barbequelarry", "cid_516_athena_commando_m_blackwidowrogue", "cid_657_athena_commando_f_techOpsBlue",
    "cid_619_athena_commando_f_techllama", "cid_660_athena_commando_f_bandageninjablue", "cid_703_athena_commando_m_cyclone", "cid_084_athena_commando_m_assassin", "cid_083_athena_commando_f_tactical",
    "cid_761_athena_commando_m_cyclonespace", "cid_783_athena_commando_m_aquajacket", "cid_964_athena_commando_m_historian_869bc", "cid_084_athena_commando_m_assassin", "cid_039_athena_commando_f_disco",
    "eid_ashtonboardwalk", "eid_ashtonsaltlake", "eid_bendy", "eid_bollywood", "eid_chicken", "cid_757_athena_commando_f_wildcat",  "cid_080_athena_commando_m_space",
    "eid_crackshotclock", "eid_dab", "eid_fireworksspin", "eid_fresh", "eid_griddles", "eid_hiphop01", "eid_iceking", "eid_kpopdance03",
    "eid_macaroon_45lhe", "eid_ridethepony_athena", "eid_robot", "eid_rockguitar", "eid_solartheory", "eid_taketheL", "eid_tapshuffle", "cid_386_athena_commando_m_streetopsstealth",
    "eid_torchsnuffer", "eid_trophycelebrationfncs", "eid_trophycelebration", "eid_twistdaytona", "eid_zest_q1k5v", "founderumbrella",
    "founderglider", "glider_id_001", "glider_id_002_medieval", "glider_id_003_district", "glider_id_004_disco", "glider_id_014_dragon",
    "glider_id_090_celestial", "glider_id_176_blackmondaycape_4p79k", "glider_id_206_donut", "umbrella_snowflake", "glider_warthog",
    "glider_voyager", "bid_001_bluesquire", "bid_002_royaleknight", "bid_004_blackknight", "bid_005_raptor", "bid_025_tactical", "eid_electroshuffle", "cid_850_athena_commando_f_skullbritecube",
    "bid_024_space", "bid_027_scavenger", "bid_029_retrogrey", "bid_030_tacticalrogue", "bid_055_psburnout", "bid_072_vikingmale",
    "bid_103_clawed", "bid_102_buckles", "bid_138_celestial", "bid_468_cyclone", "bid_520_cycloneuniverse", "halloweenscythe", "eid_floss",
    "pickaxe_id_013_teslacoil", "pickaxe_id_015_holidaycandycane", "pickaxe_id_021_megalodon", "pickaxe_id_019_heart", "cid_116_athena_commando_m_carbideblack",
    "pickaxe_id_029_assassin", "pickaxe_id_077_carbidewhite", "pickaxe_id_088_psburnout", "pickaxe_id_116_celestial", "pickaxe_id_011_medieval", "eid_takethel",
    "pickaxe_id_294_candycane", "pickaxe_id_359_cyclonemale", "pickaxe_id_376_fncs", "pickaxe_id_508_historianmale_6bqsw",
    "pickaxe_id_804_fncss20male", "pickaxe_id_stw007_basic","cid_259_athena_commando_m_streetops", "pickaxe_lockjaw"
]
def get_cosmetic_type(cosmetic_id: str):
    cid_lower = cosmetic_id.lower()
    if cid_lower.startswith("banner_"):
        return "Banners"
    elif "character_" in cid_lower or "cid_" in cid_lower:
        return "Skins"
    elif "bid_" in cid_lower or "backpack" in cid_lower:
        return "Mochilas"
    elif (
        "pickaxe_" in cid_lower
        or "pickaxe_id_" in cid_lower
        or "defaultpickaxe" in cid_lower
        or "halloweenscythe" in cid_lower
    ):
        return "Picos"
    elif "eid" in cid_lower or "emote" in cid_lower:
        return "Gestos"
    elif (
        "glider" in cid_lower
        or "founderumbrella" in cid_lower
        or "founderglider" in cid_lower
        or "solo_umbrella" in cid_lower
    ):
        return "Planeadores"
    elif "wrap" in cid_lower:
        return "Envolturas"
    elif "spray" in cid_lower:
        return "Sprays"
    else:
        return "Others"

exclusive_cosmetics = [
    'CID_017_ATHENA_COMMANDO_M',
    'CID_028_ATHENA_COMMANDO_F',
    'CID_029_ATHENA_COMMANDO_F_HALLOWEEN',
    'CID_030_ATHENA_COMMANDO_M_HALLOWEEN',
    'CID_116_ATHENA_COMMANDO_M_CARBIDEBLACK',
    'CID_315_ATHENA_COMMANDO_M_TERIYAKIFISH',
    'CID_547_ATHENA_COMMANDO_F_METEORWOMAN',
]
