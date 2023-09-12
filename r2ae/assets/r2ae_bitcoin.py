import base64
from io import BytesIO
from typing import List

import matplotlib.pyplot as plt
import pandas as pd
import requests
from dagster import AssetExecutionContext, MetadataValue, asset
from wordcloud import STOPWORDS, WordCloud



# R2AE
import pandas as pd
import requests
import matplotlib.pyplot as plt
import io, base64

@asset(
    group_name="Bitcoin Price",
    compute_kind="Python"
)
def bitcoin_raw_json(context):
    """
        Get bitcoin price via coincap API
    """
    price_url = "https://api.coincap.io/v2/assets/bitcoin/history?interval=d1"
    price_data = requests.get(price_url).json()

    context.add_output_metadata({'Number of records': len(price_data['data'])})
    return price_data

@asset(
    group_name="Bitcoin Price",
    compute_kind="Python"
)
def bitcoin_dataframe(bitcoin_raw_json):
    """
        Convert JSON Result to Pandas DataFrame
    """
    df = pd.DataFrame(bitcoin_raw_json['data'])
    df['date'] = pd.to_datetime(df['date'])
    df['priceUsd'] = df['priceUsd'].astype(float)
    
    return df
    

@asset(
    group_name="Bitcoin Price",
    compute_kind="Python"
)
def bitcoin_plot(context, bitcoin_dataframe):
    """
        Plot price data graph
    """

    plt.figure(figsize=(10, 6))
    plt.plot(bitcoin_dataframe['date'], bitcoin_dataframe['priceUsd'])
    plt.title('R2AE - Bitcoin Price Over Time')
    plt.xlabel('Date')
    plt.ylabel('Price (USD)')
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")

    # Get the content of the image and encode it to base64
    encoded_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
    buffer.close()

    # Save base64 to metadata
    markdown_code = f"![Bitcoin Price Over Time](data:image/png;base64,{encoded_image})"

    context.add_output_metadata({
        "preview": MetadataValue.md(markdown_code)
    })

# ------


@asset(group_name="hackernews", compute_kind="HackerNews API")
def hackernews_topstory_ids() -> List[int]:
    """Get up to 500 top stories from the HackerNews topstories endpoint.

    API Docs: https://github.com/HackerNews/API#new-top-and-best-stories
    """
    newstories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    top_500_newstories = requests.get(newstories_url).json()
    return top_500_newstories


@asset(group_name="hackernews", compute_kind="HackerNews API")
def hackernews_topstories(
    context: AssetExecutionContext, hackernews_topstory_ids: List[int]
) -> pd.DataFrame:
    """Get items based on story ids from the HackerNews items endpoint. It may take 1-2 minutes to fetch all 500 items.

    API Docs: https://github.com/HackerNews/API#items
    """
    results = []
    for item_id in hackernews_topstory_ids:
        item = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json").json()
        results.append(item)
        if len(results) % 20 == 0:
            context.log.info(f"Got {len(results)} items so far.")

    df = pd.DataFrame(results)

    # Dagster supports attaching arbitrary metadata to asset materializations. This metadata will be
    # shown in the run logs and also be displayed on the "Activity" tab of the "Asset Details" page in the UI.
    # This metadata would be useful for monitoring and maintaining the asset as you iterate.
    # Read more about in asset metadata in https://docs.dagster.io/concepts/assets/software-defined-assets#recording-materialization-metadata
    context.add_output_metadata(
        {
            "num_records": len(df),
            "preview": MetadataValue.md(df.head().to_markdown()),
        }
    )
    return df


@asset(group_name="hackernews", compute_kind="Plot")
def hackernews_topstories_word_cloud(
    context: AssetExecutionContext, hackernews_topstories: pd.DataFrame
) -> bytes:
    """Exploratory analysis: Generate a word cloud from the current top 500 HackerNews top stories.
    Embed the plot into a Markdown metadata for quick view.

    Read more about how to create word clouds in http://amueller.github.io/word_cloud/.
    """
    stopwords = set(STOPWORDS)
    stopwords.update(["Ask", "Show", "HN"])
    titles_text = " ".join([str(item) for item in hackernews_topstories["title"]])
    titles_cloud = WordCloud(stopwords=stopwords, background_color="white").generate(titles_text)

    # Generate the word cloud image
    plt.figure(figsize=(8, 8), facecolor=None)
    plt.imshow(titles_cloud, interpolation="bilinear")
    plt.axis("off")
    plt.tight_layout(pad=0)

    # Save the image to a buffer and embed the image into Markdown content for quick view
    buffer = BytesIO()
    plt.savefig(buffer, format="png")
    image_data = base64.b64encode(buffer.getvalue())
    md_content = f"![img](data:image/png;base64,{image_data.decode()})"

    # Attach the Markdown content as metadata to the asset
    # Read about more metadata types in https://docs.dagster.io/_apidocs/ops#metadata-types
    context.add_output_metadata({"plot": MetadataValue.md(md_content)})

    return image_data