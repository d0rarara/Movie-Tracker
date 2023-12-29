from flask import Flask, render_template, request, jsonify
import sqlite3
import requests
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

TMDB_API_KEY = os.getenv('TMDB_API_KEY')
print(TMDB_API_KEY)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/movies', methods=['POST'])
def get_movies():
    try:
        genre = request.json['genre']
        movies = query_movies_by_genre(genre)

        if not movies:
            tmdb_movies = fetch_movies_from_tmdb(genre)
            save_movies_to_database(tmdb_movies, genre)
            movies = tmdb_movies

        formatted_movies = [{'title': movie['title'], 'release_date': movie['release_date']} for movie in movies]

        return jsonify({'movies': formatted_movies})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Internal Server Error'}), 500

def query_movies_by_genre(genre):
    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT title, release_date FROM movies WHERE genre = ? ORDER BY release_date ASC', (genre,))
        movies = cursor.fetchall()

        movies_list = [{'title': movie[0], 'release_date': movie[1]} for movie in movies]

        print(f"Queried movies for genre '{genre}': {movies_list}")

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        movies_list = []

    finally:
        conn.close()

    return movies_list

def fetch_movies_from_tmdb(genre):
    url = 'https://api.themoviedb.org/3/discover/movie'
    params = {
        'api_key': TMDB_API_KEY,
        'with_genres': get_genre_id(genre),
        'sort_by': 'release_date.desc',
        'language': 'en-US',
        'page': 1,
    }
    response = requests.get(url, params=params)

    print(response.json())

    data = response.json()
    movies = []

    for movie in data['results']:
        title = movie.get('title', None)
        if title is None:
            continue
        release_date = movie.get('release_date', 'Unknown Date')

        print(f"Movie from TMDb: {title} - Release Date: {release_date}")
        print(movie)
        movies.append({'title': title, 'release_date': release_date, 'genre': genre, 'tmdb_id': movie.get('id')})

    movies.reverse()

    return movies

def get_genre_id(genre):
    genres_url = 'https://api.themoviedb.org/3/genre/movie/list'
    params = {'api_key': TMDB_API_KEY, 'language': 'en-US'}
    response = requests.get(genres_url, params=params)
    data = response.json()
    print(data)
    genre_dict = {item['name'].lower(): item['id'] for item in data['genres']}
    return genre_dict.get(genre.lower(), 18)

def save_movies_to_database(movies, genre):
    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()
    try:
        for movie in movies:
            print(f"Inserting into database: {movie}")
            cursor.execute('INSERT INTO movies (title, genre, release_date, tmdb_id) VALUES (?, ?, ?, ?)',
                           (movie['title'], genre, movie['release_date'], movie['tmdb_id']))
        conn.commit()
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)
