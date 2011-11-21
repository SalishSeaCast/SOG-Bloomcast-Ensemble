<!doctype html>
<!--[if lt IE 7]> <html class="no-js ie6 oldie" lang="en"> <![endif]-->
<!--[if IE 7]>    <html class="no-js ie7 oldie" lang="en"> <![endif]-->
<!--[if IE 8]>    <html class="no-js ie8 oldie" lang="en"> <![endif]-->
<!--[if gt IE 8]><!--> <html class="no-js" lang="en"> <!--<![endif]-->
<head>
	<meta charset="utf-8">
	<meta http-equiv="X-UA-Compatible" content="IE=edge,chrome=1">

	<title>SoG Bloomcast for ${data_date}</title>
	<meta name="description"
          content="Strait of Georgia spring diatom bloom prediction for ${bloom_date.year}">
	<meta name="author" content="Susan Allen and Doug Latornell">

	<meta name="viewport" content="width=device-width,initial-scale=1">

	<link rel="stylesheet" href="css/style.css">

	<script src="js/libs/modernizr-2.0.min.js"></script>
</head>
<body>
  <div id="header-container">
	<header class="wrapper">
      <h1 id="title">Strait of Georgia Spring Diatom Bloom Prediction</h1>
	</header>
  </div>

  <div id="main" class="wrapper">
	<article>
	  <header>
        <p>
          The current best estimate of the first spring diatom bloom
          in the Strait of Georgia is ${bloom_date}. That estimate is
          based on a run of the SOG biophysical model for deep
          estuaries with the following parameters:
        </p>
        <ul>
          <li>
            Run start date/time: ${run_start_date}
          </li>
          <li>
            Actual wind, meteorological, and river flow forcing data
            to ${data_date}, and averaged data thereafter
          </li>
        </ul>

		<h2>Disclaimer</h2>
		<p>
          Lorem ipsum dolor sit amet, consectetur adipiscing
		  elit. Aliquam sodales urna non odio egestas tempor. Nunc vel
		  vehicula ante. Etiam bibendum iaculis libero, eget molestie
		  nisl pharetra in.
        </p>
	  </header>

      <header>
        <h2>Profiles</h2>
      </header>

      <header>
        <h2>Time Series</h2>
        <object class="timeseries-graph" type="image/svg+xml"
                data="nitrate_diatoms_timeseries.svg">
        </object>
        <object class="timeseries-graph" type="image/svg+xml"
                data="temperature_salinity_timeseries.svg">
        </object>
      </header>

      <header>
        <h2>Bloom Date Evolution</h2>
        <table>
          <thead>
            <tr>
              <th>Wind Data Date</th>
              <th>Predicted Bloom Date</th>
              <th>Diatom Biomass [uM N]</th>
            </tr>
          </thead>
          <tbody>
            %for row in bloom_date_log:
              <tr>
                %for i in xrange(3):
                  <td>${row[i]}</td>
                %endfor
              </tr>
            %endfor
          </tbody>
        </table>
      </header>
    </article>
  </div>

  <div id="footer-container">
	<footer class="wrapper">
	</footer>
  </div>
</body>
</html>
