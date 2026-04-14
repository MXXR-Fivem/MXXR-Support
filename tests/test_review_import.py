from bot.services.review_service import clean_review_text, parse_legacy_review_content


def test_parse_review_with_script_comment_and_rating() -> None:
    parsed = parse_legacy_review_content(
        """
        Script : LS Custom

        Commentaire : Très bon script et très bon support

        Note : ⭐️⭐️⭐️⭐️⭐️
        """
    )

    assert parsed is not None
    assert parsed.scripts == "LS Custom"
    assert parsed.comment == "Très bon script et très bon support"
    assert parsed.rating == 5


def test_parse_review_without_explicit_script_line() -> None:
    parsed = parse_legacy_review_content(
        """
        Rien à dire sur le service. Dès qu'on a un soucis ou des questions par rapport au script,
        on a aussitôt une réponse et de l'aide.

        Note : ⭐⭐⭐⭐⭐
        """
    )

    assert parsed is not None
    assert parsed.scripts == "Non précisé"
    assert "Rien à dire sur le service." in parsed.comment
    assert parsed.rating == 5


def test_parse_review_with_metric_lines() -> None:
    parsed = parse_legacy_review_content(
        """
        Script : Garage
        ⭐⭐⭐⭐⭐  | Prix 5/5
        ⭐⭐⭐⭐⭐ | Support 5/5
        ⭐⭐⭐⭐⭐ | Performance 5/5
        Très bon support, problème de onesync réglé en peu de temps, je recommande 😉
        """
    )

    assert parsed is not None
    assert parsed.scripts == "Garage"
    assert parsed.comment == "Très bon support, problème de onesync réglé en peu de temps, je recommande 😉"
    assert parsed.rating == 5


def test_parse_legacy_review_with_textual_stars_and_purchase_sentence() -> None:
    parsed = parse_legacy_review_content(
        """
        10 étoiles pour ce support et script de qualité mdrrrr je vous recommande fortement ce dev { script banque + garage)
        """
    )

    assert parsed is not None
    assert parsed.scripts == "banque + garage"
    assert "support et script de qualité" in parsed.comment
    assert parsed.rating == 5


def test_parse_legacy_review_without_explicit_rating_defaults_to_five() -> None:
    parsed = parse_legacy_review_content(
        """
        bonjour tous le monde, jai acheter le catalogue concess , c'est vraiment du bon taff,
        si vous avez besoin d'aide il vous aide a le setup. Au top
        """
    )

    assert parsed is not None
    assert parsed.scripts == "concess"
    assert "vraiment du bon taff" in parsed.comment
    assert parsed.rating == 5


def test_parse_legacy_multiline_script_list() -> None:
    parsed = parse_legacy_review_content(
        """
        Bonjour,

        j'ai acheter trois script

        garage
        Gouv
        banquier

        tous bien fait en cas de problème il répond très vite et corrige si il y'a un souci
        """
    )

    assert parsed is not None
    assert parsed.scripts == "garage, Gouv, banquier"
    assert "il répond très vite" in parsed.comment
    assert parsed.rating == 5


def test_clean_review_text_removes_discord_artifacts_and_markdown() -> None:
    cleaned = clean_review_text(
        "Merci <@123456789> **énormément** pour le support\n"
        "Voir aussi [le lien](https://example.com) et @everyone"
    )

    assert "<@" not in cleaned
    assert "**" not in cleaned
    assert "@everyone" not in cleaned
    assert "le lien" in cleaned
