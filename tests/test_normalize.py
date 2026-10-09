from app.evaluation.normalize import (
    contains_phrase,
    extract_all_labeled_values,
    extract_entities,
    extract_labeled_values,
    extract_numbers,
    jaccard,
    normalize_text,
    overlap,
    singular,
    split_sentences,
    tokenize,
    word_count,
)


def test_normalize_lowercases_and_strips_punctuation():
    assert normalize_text("Refund, window: 30-DAYS!") == "refund window 30 days"


def test_normalize_strips_accents_and_curly_quotes():
    assert normalize_text("caf\u00e9 \u201cquoted\u201d") == "cafe quoted"


def test_tokenize_drops_stopwords_and_single_chars():
    assert tokenize("The refund of 30 days is a policy") == [
        "refund",
        "30",
        "days",
        "policy",
    ]


def test_tokenize_keeps_stopwords_when_asked():
    assert "the" in tokenize("the refund", keep_stopwords=True)


def test_split_sentences_is_decimal_safe():
    text = "The total is 14.50 dollars. Refunds take 3 days. Nothing else applies."
    assert len(split_sentences(text)) == 3


def test_split_sentences_empty_input():
    assert split_sentences("") == []


def test_extract_numbers_handles_currency_and_grouping():
    assert extract_numbers("You owe $1,299.50 today") == [1299.50]


def test_extract_numbers_ignores_ordinals_and_versions():
    assert extract_numbers("It is 1st on the list") == []


def test_extract_numbers_keeps_hyphenated_day_counts():
    assert extract_numbers("delivered in 2-day shipping") == [2]


def test_extract_entities_keeps_real_names():
    entities = extract_entities("Amazon shipped it. The order left on 12 March.")
    assert "Amazon" in entities


def test_extract_entities_drops_sentence_initial_common_words():
    entities = extract_entities("The order is ready. Please collect it.")
    assert "The" not in entities
    assert "Please" not in entities


def test_extract_labeled_values_uses_preceding_content_words():
    values = extract_labeled_values("The refund amount of 500 dollars was issued.")
    assert 500.0 in values.values()


def test_extract_labeled_values_skips_stopword_labels():
    assert extract_labeled_values("There were 42 issues.") == {}


def test_extract_all_labeled_values_keeps_repeats():
    pairs = extract_all_labeled_values(
        "The refund amount of 500 was issued and the refund amount of 900 was confirmed."
    )
    values = [v for _, v in pairs]
    assert 500.0 in values and 900.0 in values


def test_jaccard_and_overlap_behaviour():
    a = {"refund", "window", "days"}
    b = {"refund", "window", "days", "policy", "offer"}
    assert jaccard(a, b) == 3 / 5
    assert overlap(a, b) == 1.0


def test_jaccard_empty_sets_are_equal():
    assert jaccard(set(), set()) == 1.0
    assert jaccard({"a"}, set()) == 0.0


def test_contains_phrase_respects_word_boundaries():
    text = normalize_text("refunded orders are not available")
    assert contains_phrase(text, "refund") is False


def test_contains_phrase_tolerates_simple_plurals():
    text = normalize_text("Refunds are available under our policies.")
    assert contains_phrase(text, "refund") is True
    assert contains_phrase(text, "policy") is True


def test_singular_handles_common_endings():
    assert singular("policies") == "policy"
    assert singular("boxes") == "box"
    assert singular("refunds") == "refund"
    assert singular("class") == "class"


def test_word_count_counts_whitespace_separated_words():
    assert word_count("one two three") == 3