active_indices = ["persons", "genres"]

pg_extract_queries = {
    "persons": """
                SELECT
                    p.id
                    , p.full_name
                    , p.modified
                FROM content.person p
                """,
    "genres": """
                SELECT
                    g.id
                    , g.name
                    , g.modified
                FROM content.genre g
                """
}

index_attr_list = {
    "persons": ["id", "full_name"],
    "genres": ["id", "name"]
}

# Название атрибута с временем обновления последней записи, загруженной в ES, в файле конфигурации
state_attr_name_in_json = {
    "persons": "last_checked_persons_ts",
    "genres": "last_checked_genres_ts"
}

schemas = {
    "persons": """
{
  "settings": {
    "refresh_interval": "1s",
    "analysis": {
      "filter": {
        "english_stop": {
          "type":       "stop",
          "stopwords":  "_english_"
        },
        "english_stemmer": {
          "type": "stemmer",
          "language": "english"
        },
        "english_possessive_stemmer": {
          "type": "stemmer",
          "language": "possessive_english"
        },
        "russian_stop": {
          "type":       "stop",
          "stopwords":  "_russian_"
        },
        "russian_stemmer": {
          "type": "stemmer",
          "language": "russian"
        }
      },
      "analyzer": {
        "ru_en": {
          "tokenizer": "standard",
          "filter": [
            "lowercase",
            "english_stop",
            "english_stemmer",
            "english_possessive_stemmer",
            "russian_stop",
            "russian_stemmer"
          ]
        }
      }
    }
  },
  "mappings": {
    "dynamic": "strict",
    "properties": {
      "id": {
        "type": "keyword"
      },
      "full_name": {
        "type": "text",
        "analyzer": "ru_en"
        }
      }
    }
  }
}
""",

    "genres": """
{
  "settings": {
    "refresh_interval": "1s",
    "analysis": {
      "filter": {
        "english_stop": {
          "type":       "stop",
          "stopwords":  "_english_"
        },
        "english_stemmer": {
          "type": "stemmer",
          "language": "english"
        },
        "english_possessive_stemmer": {
          "type": "stemmer",
          "language": "possessive_english"
        },
        "russian_stop": {
          "type":       "stop",
          "stopwords":  "_russian_"
        },
        "russian_stemmer": {
          "type": "stemmer",
          "language": "russian"
        }
      },
      "analyzer": {
        "ru_en": {
          "tokenizer": "standard",
          "filter": [
            "lowercase",
            "english_stop",
            "english_stemmer",
            "english_possessive_stemmer",
            "russian_stop",
            "russian_stemmer"
          ]
        }
      }
    }
  },
  "mappings": {
    "dynamic": "strict",
    "properties": {
      "id": {
        "type": "keyword"
      },
      "name": {
        "type": "keyword"
        },
      "description": {
        "type": "text",
        "analyzer": "ru_en"
        }
      }
    }
  }
}
"""
}
