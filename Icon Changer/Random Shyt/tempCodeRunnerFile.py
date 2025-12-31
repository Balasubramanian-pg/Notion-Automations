import requests
from bs4 import BeautifulSoup
import pandas as pd

url = "https://www.nobroker.in/property/rent/pune/Baner?searchParam=W3sibGF0IjoxOC41NjQyNDUyLCJsb24iOjczLjc3Njg1MTEsInBsYWNlSWQiOiJDaElKeTlOZDhNLS13anNSZmF0Xy01Y1NrYUUiLCJwbGFjZU5hbWUiOiJCYW5lciJ9XQ==&radius=2.0&sharedAccomodation=0&type=BHK1&availability=within_15_days&city=pune&locality=Baner"

headers = {"User-Agent": "Mozilla/5.0"}
response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

# Each property card container
cards = soup.find_all("section", {"class": "group"})

data = []
for card in cards:
    entry = {}
    try:
        # Title & URL
        title_tag = card.find("a", href=True)
        entry["Title"] = title_tag.get_text(strip=True)
        entry["URL"] = "https://www.nobroker.in" + title_tag["href"]

        # Project / address
        project = card.find("a", {"href": lambda x: x and "prjt" in x})
        entry["Project"] = project.get_text(strip=True) if project else ""
        address = card.find("div", class_="mt-0.5p")
        entry["Address"] = address.get_text(" ", strip=True) if address else ""

        # Rent / deposit / built-up area
        overview = card.find_next("div", class_="nb__7nqQI")
        if overview:
            values = overview.find_all("div", class_="font-semi-bold")
            labels = overview.find_all("div", class_="heading-7")
            for label, value in zip(labels, values):
                entry[label.get_text(strip=True)] = value.get_text(strip=True)

        # Furnishing, apartment type, tenant, availability
        blocks = card.find_all("div", class_="font-semibold")
        labels = card.find_all("div", class_="heading-7")
        for label, value in zip(labels, blocks):
            entry[label.get_text(strip=True)] = value.get_text(strip=True)

        # Optional fields
        if card.find(string="Posh Society"):
            entry["Society Tag"] = "Posh Society"

    except Exception as e:
        print("Error parsing card:", e)
    if entry:
        data.append(entry)

# Convert to DataFrame and Excel
df = pd.DataFrame(data)
df.to_excel("nobroker_baner_properties.xlsx", index=False)
print(f"Saved {len(df)} listings to nobroker_baner_properties.xlsx")
