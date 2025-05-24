import re

# Read the main.py file
with open('app/main.py', 'r') as file:
    content = file.read()

# Find and replace the problematic code section
fixed_content = content.replace(
    "// Render the filtered and sorted data\n                renderSummaryTable(filteredData);\n            }\n                });",
    "// Render the filtered and sorted data\n                renderSummaryTable(filteredData);\n            }"
)

# Write the fixed content back to the file
with open('app/main.py', 'w') as file:
    file.write(fixed_content)

print("Fixed the JavaScript syntax error in the dashboard HTML template.")