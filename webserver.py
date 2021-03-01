from quart import *

app = Quart(__name__)

@app.route('/')
async def index(request):
    data = {"the best bot": "yes"}
    return jsonify(data)

app.run()
