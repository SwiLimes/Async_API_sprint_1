from uuid import UUID


class Transformer:
    def transform(self, rows: list[dict]) -> list[dict]:
        if not rows:
            return []

        films: dict[UUID, dict] = {}

        for row in rows:
            fw_id = row['fw_id']
            if fw_id not in films:
                films[fw_id] = {
                    'uuid': str(fw_id),
                    'title': row['title'],
                    'description': row['description'] or '',
                    'imdb_rating': row['rating'],
                    'genre': {},
                    'actors': {},
                    'directors': {},
                    'writers': {},
                }

            genre_id = row.get('genre_id')
            genre_name = row.get('genre_name')
            if genre_id and genre_name:
                films[fw_id]['genre'][genre_id] = {
                    'uuid': str(genre_id),
                    'name': genre_name,
                }

            role = row.get('role')
            person_id = row.get('person_id')
            full_name = row.get('full_name')
            if role and person_id and full_name:
                person = {'uuid': str(person_id), 'name': full_name}
                if role == 'actor':
                    films[fw_id]['actors'][person_id] = person
                elif role == 'director':
                    films[fw_id]['directors'][person_id] = person
                elif role == 'writer':
                    films[fw_id]['writers'][person_id] = person

        return [
            self._to_doc(film)
            for film in sorted(films.values(), key=lambda item: item['uuid'])
        ]

    @staticmethod
    def _sorted_values(items: dict) -> list[dict]:
        return sorted(items.values(), key=lambda item: item['name'])

    def _to_doc(self, film: dict) -> dict:
        actors = self._sorted_values(film['actors'])
        directors = self._sorted_values(film['directors'])
        writers = self._sorted_values(film['writers'])
        genres = sorted(film['genre'].values(), key=lambda item: item['name'])

        doc = {
            'uuid': film['uuid'],
            'title': film['title'],
            'description': film['description'],
            'genre': genres,
            'actors': actors,
            'directors': directors,
            'writers': writers,
            'actors_names': [person['name'] for person in actors],
            'directors_names': [person['name'] for person in directors],
            'writers_names': [person['name'] for person in writers],
        }
        if film['imdb_rating'] is not None:
            doc['imdb_rating'] = film['imdb_rating']
        return doc
