from supabase import create_client

url = "https://mqoqdddzrwvonklsprgb.supabase.co/"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1xb3FkZGR6cnd2b25rbHNwcmdiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzI2NjIyNDEsImV4cCI6MjA0ODIzODI0MX0.18AdLB9xAb8rN2-G9YIiyjoH-u7uaReXqbelkzZXGPI"
client = create_client(url, key)
print("Client created:", client)
