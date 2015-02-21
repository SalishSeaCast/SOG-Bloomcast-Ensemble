# rsync ensemble bloomcast prediction results to shelob web server

HTML_DIR=www/salishsea-site/site/_build/html
SHELOB=shelob:/www/salishsea/data
rsync -Rtvh $HTML_DIR/./bloomcast/spring_diatoms.html $SHELOB
rsync -rRtvh $HTML_DIR/./_static/bloomcast/spring_diatoms/ $SHELOB
