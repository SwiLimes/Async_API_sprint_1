MAPPING_MOVIES = {
    "body": {
        "mappings": {
            "properties": {
                "id": {"type": "keyword"},
                "imdb_rating": {"type": "float"},
                "genre": {
                    "type": "nested",
                    "properties": {
                        "id": {"type": "keyword"},
                        "name": {"type": "text"}
                    }
                },
                "title": {"type": "text"},
                "description": {"type": "text"},
                "director": {"type": "keyword"},
                "actors_names": {"type": "keyword"},
                "writers_names": {"type": "keyword"},
                "actors": {
                    "type": "nested",
                    "properties": {
                        "id": {"type": "keyword"},
                        "name": {"type": "text"}
                    }
                },
                "writers": {
                    "type": "nested",
                    "properties": {
                        "id": {"type": "keyword"},
                        "name": {"type": "text"}
                    }
                },
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"},
                "film_work_type": {"type": "keyword"}
            }
        }
    }
}
