from flask import Flask, render_template, request
import pandas as pd
import plotly.express as px
import json
import plotly
from plotly.utils import PlotlyJSONEncoder
import io

app = Flask(__name__)

def find_header(file_stream):
    file_stream.seek(0)  # Go to the start of the file
    for i, line in enumerate(file_stream):
        if 'First Name' in line:
            return i
    return 0  # Default to the first line if the header is not found

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['file']
        if file:
            file_stream = io.StringIO(file.stream.read().decode('utf-8'), newline=None)
            header_row = find_header(file_stream)
            file_stream.seek(0)
            df = pd.read_csv(file_stream, skiprows=header_row)
            df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]
            df['connected_on'] = pd.to_datetime(df['connected_on'], errors='coerce')
            df['month_year'] = df['connected_on'].dt.to_period('M')
            return process_data(df)
    return render_template('index.html')

def process_data(df):
    # Handle date parsing with a specific format
    df['connected_on'] = pd.to_datetime(df['connected_on'], errors='coerce')

    # Analysis 1: Total number of connections
    num_connections = df.shape[0]

    # Analysis 2: Top 10 companies
    top_companies_fig = px.bar(df['company'].value_counts().head(10), orientation='h', labels={'value': 'Number of Connections', 'index': 'Company'}, title="Top 10 Companies")
    top_companies_fig.update_layout(yaxis={'categoryorder':'total ascending'})

    # Analysis 3: Top 10 positions
    top_positions_fig = px.bar(df['position'].value_counts().head(10), orientation='h', labels={'value': 'Number of Connections', 'index': 'Position'}, title="Top 10 Positions")

    # Analysis 4: Distribution of 'connected_on' dates
    connections_date_fig = px.histogram(df, x='connected_on', nbins=15, title="Connections over Time")

    # Analysis 5: Emails table
    emails_df = df[df["email_address"].notnull()]
    emails_table_html = emails_df.to_html(classes='table table-striped', index=False)
    # New analyses
    latest_connections = df.sort_values(by='connected_on', ascending=False).head(10)
    earliest_connections = df.sort_values(by='connected_on', ascending=True).head(10)
    
    connections_over_time = df.set_index('connected_on').resample('D').size()
    cumulative_connections = connections_over_time.cumsum()
    cumulative_connections_fig = px.line(
        x=cumulative_connections.index, 
        y=cumulative_connections.values, 
        labels={'x': 'Date', 'y': 'Cumulative Connections'}, 
        title='Cumulative Connections Over Time'
    )

    general_analysis = {
        'Total Connections': len(df),
        'Unique Companies': len(df['company'].unique()),
        'Unique Positions': len(df['position'].unique()),
        'Earliest Connection': earliest_connections['connected_on'].min().strftime('%B %d, %Y') if not earliest_connections.empty else 'N/A',
        'Latest Connection': latest_connections['connected_on'].max().strftime('%B %d, %Y') if not latest_connections.empty else 'N/A',
    }

    # Encode the figures for JavaScript
    graphsJSON = json.dumps({
        'top_companies_fig': top_companies_fig,
        'top_positions_fig': top_positions_fig,
        'connections_date_fig': connections_date_fig,
        'cumulative_connections_fig': cumulative_connections_fig,
        'emails_table_html': emails_table_html  # Add the emails table HTML here
    }, cls=PlotlyJSONEncoder)

    # Render the template with all the analysis data
    return render_template('report.html', 
                           num_connections=len(df),
                           latest_connections=latest_connections.to_html(classes='table table-striped', index=False),
                           earliest_connections=earliest_connections.to_html(classes='table table-striped', index=False),
                           general_analysis=general_analysis,
                           graphsJSON=graphsJSON)

if __name__ == '__main__':
    app.run(debug=True)
