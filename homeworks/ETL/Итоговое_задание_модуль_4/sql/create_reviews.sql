CREATE TABLE reviews (
    offering_id Utf8,
    user_id Utf8,
    overall Double,
    value Double,
    service Double,
    location Double,
    rooms Double,
    cleanliness Double,
    sleep_quality Double,
    review_text Utf8,
    PRIMARY KEY (offering_id)
);