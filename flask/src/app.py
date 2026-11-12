from flask import Flask, render_template
import folium

app = Flask(__name__, template_folder='../templates', static_folder='../static')

@app.route('/')
def index():
    # Create a simple map
    m = folium.Map(location=[37.7749, -122.4194], zoom_start=13)
    folium.Marker([37.7749, -122.4194], popup='San Francisco').add_to(m)
    
    # Save map to HTML string
    map_html = m._repr_html_()
    
    return render_template('index.html', map_html=map_html)

if __name__ == '__main__':
    app.run(debug=True)