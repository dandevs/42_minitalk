CC = cc
CFLAGS = -g
# CFLAGS = -Wall -Wextra -Werror -Isrc/shared
SRCDIR = src

CLIENT_SRC = $(shell find $(SRCDIR)/client $(SRCDIR)/shared -name "*.c")
SERVER_SRC = $(shell find $(SRCDIR)/server $(SRCDIR)/shared -name "*.c")

CLIENT = client
SERVER = server

all: $(CLIENT) $(SERVER)

$(CLIENT): $(CLIENT_SRC)
	$(CC) $(CFLAGS) -o $(CLIENT) $(CLIENT_SRC)

$(SERVER): $(SERVER_SRC)
	$(CC) $(CFLAGS) -o $(SERVER) $(SERVER_SRC)

clean:
	rm -f $(CLIENT) $(SERVER)

fclean: clean

re: fclean all

.PHONY: all clean fclean re
