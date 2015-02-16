# rsync ensemble bloomcast prediction results to shelob web server

HTML_DIR=www/salishsea-site/site/_build/html
SHELOB=shelob:/www/salishsea/data
rsync -Rtvhz $HTML_DIR/./bloomcast/spring_diatoms.html $SHELOB
rsync -rRtvhz $HTML_DIR/./_static/bloomcast/spring_diatoms/ $SHELOB
