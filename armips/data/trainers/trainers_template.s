
trainerdata NUMBER, "Name"
    trainermontype TRAINER_DATA_TYPE_ITEMS | TRAINER_DATA_TYPE_MOVES | TRAINER_DATA_TYPE_ABILITY | TRAINER_DATA_TYPE_BALL | TRAINER_DATA_TYPE_IV_EV_SET | TRAINER_DATA_TYPE_NATURE_SET | TRAINER_DATA_TYPE_SHINY_LOCK | 0
    trainerclass TRAINERCLASS_PKMN_TRAINER_RED
    nummons 1
    item ITEM_NONE
    item ITEM_NONE
    item ITEM_NONE
    item ITEM_NONE
    aiflags F_PRIORITIZE_SUPER_EFFECTIVE | F_EVALUATE_ATTACKS | F_EXPERT_ATTACKS | 0
    battletype SINGLE_BATTLE
    endentry

    party NUMBER
        // mon 0
        ivs 0
        abilityslot 0
        level 5
        pokemon SET_ME
        item ITEM_NONE
        move MOVE_NONE
        move MOVE_NONE
        move MOVE_NONE
        move MOVE_NONE
        ability SET_ME
        ball ITEM_POKE_BALL
        setivs 15, 15, 15, 15, 15, 15
        setevs 0, 0, 0, 0, 0, 0
        nature NATURE_
        shinylock 0
        ballseal 0
    endparty
