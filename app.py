# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#

import babel.dates
import dateutil.parser
from flask import (Flask, render_template, request, flash, redirect, url_for)
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from sqlalchemy.exc import SQLAlchemyError
from wtforms import ValidationError
from forms import *
from datetime import datetime

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)


# ----------------------------------------------------------------------------#
# Models.
# ----------------------------------------------------------------------------#
class Venue(db.Model):
    __tablename__ = 'venues'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    genres = db.Column("genres", db.ARRAY(db.String()), nullable=False)
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(250))
    seeking_talent = db.Column(db.Boolean, default=True)
    seeking_description = db.Column(db.String(250))
    shows = db.relationship('Show', backref='venue', lazy=True)

    def __repr__(self):
        return f'<Venue {self.id} name: {self.name}>'


class Artist(db.Model):
    __tablename__ = 'artists'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120))
    genres = db.Column(db.ARRAY(db.String()), nullable=False)
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    shows = db.relationship('Show', backref='artist', lazy=True)

    def __repr__(self):
        return f'<Artist {self.id} name: {self.name}>'


class Show(db.Model):
    __tablename__ = 'shows'

    id = db.Column(db.Integer, primary_key=True)
    artist_id = db.Column(db.Integer, db.ForeignKey('artists.id'), nullable=False)
    venue_id = db.Column(db.Integer, db.ForeignKey('venues.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<Show {self.id}, Artist {self.artist_id}, Venue {self.venue_id}>'


# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#
def format_datetime(value, date_format='medium'):
    date = dateutil.parser.parse(value)
    if date_format == 'full':
        date_format = "EEEE MMMM, d, y 'at' h:mma"
    elif date_format == 'medium':
        date_format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, date_format)


app.jinja_env.filters['datetime'] = format_datetime


# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#

@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    """ Method to display venues per city and state and list them in venue page """

    data = []
    unique_locations = set()
    all_venues = Venue.query.all()

    # Search for only unique venues
    for venue in all_venues:
        unique_locations.add((venue.city, venue.state))

    for unique_spot in unique_locations:
        data.append({
            "city": unique_spot[0],
            "state": unique_spot[1],
            "venues": []
        })

    for venue in all_venues:
        num_upcoming_shows = 0

        all_shows = Show.query.filter_by(venue_id=venue.id).all()

        current_date = datetime.now()

        # Count for upcoming shows after current date
        for show in all_shows:
            if show.start_time > current_date:
                num_upcoming_shows += 1

        #
        for unique_venue in data:
            # Show existing venues with shows
            if venue.city == unique_venue['city'] and venue.state == unique_venue['state']:
                unique_venue['venues'].append({
                    "id": venue.id,
                    "name": venue.name,
                    "num_upcoming_shows": num_upcoming_shows
                })
    return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    """ Method to search venues based on user input term """
    search_term = request.form.get('search_term', '')
    data = Venue.query.filter(Venue.name.ilike(f'%{search_term}%'))

    # Search for venue depending on criteria
    results = {
        "count": data.count(),
        "data": data
    }
    return render_template('pages/search_venues.html', results=results, search_term=search_term)


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    """ Method to display individual venues based on user venue_id """
    # Shows the venue page with the given venue_id
    venue = Venue.query.get(venue_id)

    current_time = datetime.now()

    # Search for upcoming shows
    upcoming_shows_query = db.session.query(Show).join(Venue, Show.venue_id == venue.id).filter(
        Show.start_time > current_time).all()
    upcoming_shows = []

    # Search for past shows
    past_shows_query = db.session.query(Show).join(Venue, Show.venue_id == venue.id).filter(
        Show.start_time < current_time).all()
    past_shows = []

    # Search for upcoming and previous shows
    for query in upcoming_shows_query:
        data = {
            "artist_id": query.artist.id,
            "artist_name": query.artist.name,
            "artist_image_link": query.artist.image_link,
            "start_time": format_datetime(str(query.start_time))
        }
        upcoming_shows.append(data)

    for show in past_shows_query:
        data = {
            "artist_id": show.artist_id,
            "artist_name": show.artist.name,
            "artist_image_link": show.artist.image_link,
            "start_time": format_datetime(str(show.start_time))
        }
        past_shows.append(data)

    # Display past and upcoming shows per venue
    data = {
        "id": venue.id,
        "name": venue.name,
        "genres": venue.genres,
        "address": venue.address,
        "city": venue.city,
        "state": venue.state,
        "phone": venue.phone,
        "website": venue.website,
        "facebook_link": venue.facebook_link,
        "seeking_talent": venue.seeking_talent,
        "seeking_description": venue.seeking_description,
        "image_link": venue.image_link,
        "past_shows": past_shows,
        "upcoming_shows": upcoming_shows,
        "past_shows_count": len(past_shows),
        "upcoming_shows_count": len(upcoming_shows)
    }

    return render_template('pages/show_venue.html', venue=data)


#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    """ Method to post venue """
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    """ Method to save venue in database """
    try:
        # get form data and create
        form = VenueForm()
        venue = Venue(name=form.name.data, city=form.city.data, state=form.state.data, address=form.address.data,
                      phone=form.phone.data, image_link=form.image_link.data, facebook_link=form.facebook_link.data,
                      seeking_description=form.seeking_description.data, seeking_talent=form.seeking_talent.data,
                      website=form.website.data, genres=form.genres.data)

        if not form.validate_phone(venue.phone):
            db.session.rollback()
            flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')
            # closes session
            db.session.close()
            return render_template('pages/home.html')

        # commit session to database
        db.session.add(venue)
        db.session.commit()

        # flash success
        flash('Venue ' + request.form['name'] + ' was successfully listed!')
    except SQLAlchemyError:
        # catches errors
        db.session.rollback()
        flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')
    finally:
        # closes session
        db.session.close()
    return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    """ Method to delete venues based on venue id """
    venue_name = ''
    try:
        # Get venue by ID
        venue = Venue.query.get(venue_id)
        venue_name = venue.name

        db.session.delete(venue)
        db.session.commit()

        flash('Venue ' + venue_name + ' was deleted')
    except SQLAlchemyError:
        flash('an error occurred and Venue ' + venue_name + ' was not deleted')
        db.session.rollback()
    finally:
        db.session.close()

    return redirect(url_for('index'))


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
    """ Method to display artists """
    data = []

    all_artists = Artist.query.all()

    for artist in all_artists:
        data.append({
            "id": artist.id,
            "name": artist.name
        })
    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    """ Method to search artists based on user input term """

    search_term = request.form.get('search_term', '')

    # filter artists by case insensitive search
    result = Artist.query.filter(Artist.name.ilike(f'%{search_term}%'))

    response = {
        "count": result.count(),
        "data": result
    }

    return render_template('pages/search_artists.html', results=response,
                           search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    """ Method to show individual artists based on artist id """

    artist = Artist.query.get(artist_id)

    current_time = datetime.now()

    # Search for upcoming shows
    upcoming_shows_query = db.session.query(Show).join(Artist, Show.artist_id == artist.id).filter(
        Show.start_time > current_time).all()
    upcoming_shows = []

    # Search for past shows
    past_shows_query = db.session.query(Show).join(Artist, Show.artist_id == artist.id).filter(
        Show.start_time < current_time).all()
    past_shows = []

    # Search for upcoming and previous shows
    for query in upcoming_shows_query:
        data = {
            "venue_id": query.venue.id,
            "venue_name": query.venue.name,
            "venue_image_link": query.venue.image_link,
            "start_time": format_datetime(str(query.start_time))
        }
        upcoming_shows.append(data)

    for query in past_shows_query:
        data = {
            "artist_id": query.venue.id,
            "artist_name": query.venue.name,
            "artist_image_link": query.venue.image_link,
            "start_time": format_datetime(str(query.start_time))
        }
        past_shows.append(data)

    data = {
        "id": artist.id,
        "name": artist.name,
        "genres": artist.genres,
        "city": artist.city,
        "state": artist.state,
        "phone": artist.phone,
        "facebook_link": artist.facebook_link,
        "image_link": artist.image_link,
        "past_shows": past_shows,
        "upcoming_shows": upcoming_shows,
        "past_shows_count": len(past_shows),
        "upcoming_shows_count": len(upcoming_shows)
    }

    return render_template('pages/show_artist.html', artist=data)


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    """ Method to edit individual artists based on artist id """

    form = ArtistForm()

    artist = Artist.query.get(artist_id)

    artist_data = {
        "id": artist.id,
        "name": artist.name,
        "genres": artist.genres,
        "city": artist.city,
        "state": artist.state,
        "phone": artist.phone,
        "facebook_link": artist.facebook_link,
        "image_link": artist.image_link
    }

    return render_template('forms/edit_artist.html', form=form, artist=artist_data)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    """ Method to save edits on individual artist to database """

    try:
        form = ArtistForm()
        artist = Artist.query.get(artist_id)
        artist.name = form.name.data
        artist.phone = form.phone.data
        artist.state = form.state.data
        artist.city = form.city.data
        artist.genres = form.genres.data
        artist.image_link = form.image_link.data
        artist.facebook_link = form.facebook_link.data

        if not form.validate_phone(artist.phone):
            db.session.rollback()
            flash('An error occurred. Artist ' + request.form['name'] + ' could not be edited.')
            # closes session
            db.session.close()
            return render_template('pages/home.html')

        db.session.commit()
        flash('The Artist ' + request.form['name'] + ' has been successfully updated!')
    except SQLAlchemyError:
        db.session.rolback()
        flash('An Error has occured and the update unsuccessful')
    finally:
        db.session.close()

    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    """ Method to edit individual venues based on venues id """

    form = VenueForm()
    venue = Venue.query.get(venue_id)
    venue = {
        "id": venue.id,
        "name": venue.name,
        "genres": venue.genres,
        "address": venue.address,
        "city": venue.city,
        "state": venue.state,
        "phone": venue.phone,
        "website": venue.website,
        "facebook_link": venue.facebook_link,
        "seeking_talent": venue.seeking_talent,
        "seeking_description": venue.seeking_description,
        "image_link": venue.image_link,
    }

    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    """ Method to save edits on individual venues to database """

    try:
        form = VenueForm()
        venue = Venue.query.get(venue_id)
        name = form.name.data

        venue.name = name
        venue.genres = form.genres.data
        venue.city = form.city.data
        venue.state = form.state.data
        venue.address = form.address.data
        venue.phone = form.phone.data
        venue.facebook_link = form.facebook_link.data
        venue.website = form.website.data
        venue.image_link = form.image_link.data
        venue.seeking_talent = form.seeking_talent.data
        venue.seeking_description = form.seeking_description.data

        if not form.validate_phone(venue.phone):
            db.session.rollback()
            flash('An error occurred. Venue ' + request.form['name'] + ' could not be edited.')
            # closes session
            db.session.close()
            return render_template('pages/home.html')

        db.session.commit()
        flash('Venue ' + name + ' has been updated')
    except SQLAlchemyError:
        db.session.rollback()
        flash('An error occured while trying to update Venue')
    finally:
        db.session.close()

    return redirect(url_for('show_venue', venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    """ Method to post artists """

    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    """ Method to save artists in database """

    try:
        form = ArtistForm()

        artist = Artist(name=form.name.data, city=form.city.data, state=form.state.data,
                        phone=form.phone.data, genres=form.genres.data,
                        image_link=form.image_link.data, facebook_link=form.facebook_link.data)

        if not form.validate_phone(artist.phone):
            db.session.rollback()
            flash('An error occurred. Artist ' + request.form['name'] + ' could not be created.')
            # closes session
            db.session.close()
            return render_template('pages/home.html')

        db.session.add(artist)
        db.session.commit()

        flash('Artist ' + request.form['name'] + ' was successfully listed!')
    except SQLAlchemyError:
        db.session.rollback()
        flash('An error occurred. Artist ' + request.form['name'] + ' could not be listed.')
    finally:
        db.session.close()

    return render_template('pages/home.html')


@app.route('/artist/<artist_id>', methods=['DELETE'])
def delete_artist(artist_id):
    """ Method to delete artists based on artist id """

    artist_name = ''
    try:

        artist = Artist.query.get(artist_id)
        artist_name = artist.name

        db.session.delete(artist)
        db.session.commit()

        flash('Artist ' + artist_name + ' was deleted')
    except SQLAlchemyError:
        flash('an error occurred and Artist ' + artist_name + ' was not deleted')
        db.session.rollback()
    finally:
        db.session.close()

    return redirect(url_for('index'))


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    """ Method to display shows by start time """

    all_shows = Show.query.order_by(db.desc(Show.start_time))

    data = []

    for show in all_shows:
        data.append({
            "venue_id": show.venue_id,
            "venue_name": show.venue.name,
            "artist_id": show.artist_id,
            "artist_name": show.artist.name,
            "artist_image_link": show.artist.image_link,
            "start_time": format_datetime(str(show.start_time))
        })

    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    """ Method to post shows """

    # renders form
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    """ Method to save shows in database """

    try:
        show = Show(artist_id=request.form['artist_id'], venue_id=request.form['venue_id'],
                    start_time=request.form['start_time'])

        db.session.add(show)
        db.session.commit()

        flash('Show was successfully listed!')
    except SQLAlchemyError:
        db.session.rollback()
        flash('An error occurred. Show could not be listed.')
    finally:
        db.session.close()

    return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
