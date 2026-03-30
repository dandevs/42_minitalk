/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   client.c                                           :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: danimend <danimend@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/03/30 03:47:57 by danimend          #+#    #+#             */
/*   Updated: 2026/03/30 05:47:39 by danimend         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <signal.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include "../shared/lib.h"

static volatile int	g_can_write;

static void	handler(int sig)
{
	if (sig == SIGUSR1)
		g_can_write = 1;
	else
	{
		g_can_write = -1;
		ft_write_str(1, "\n-- SERVER ACKNOWLEDGED --\n");
	}
}

static void	setup_signals(void)
{
	struct sigaction	sa;

	sa.sa_handler = handler;
	sigemptyset(&sa.sa_mask);
	sa.sa_flags = 0;
	sigaction(SIGUSR1, &sa, NULL);
	sigaction(SIGUSR2, &sa, NULL);
}

static void	send_char(pid_t pid, unsigned char c)
{
	int	bit;

	bit = 0;
	while (bit < 8 && g_can_write != -1)
	{
		g_can_write = 0;
		if (c & (1 << bit))
			kill(pid, SIGUSR1);
		else
			kill(pid, SIGUSR2);
		while (g_can_write == 0)
			pause();
		bit++;
	}
}

int	main(int argc, char **argv)
{
	pid_t	pid;
	char	*str;
	int		i;

	if (argc != 3)
	{
		ft_write_str(2, "Invalid parameters");
		return (1);
	}
	pid = atoi(argv[1]);
	if (pid <= 0 || kill(pid, 0) == -1)
	{
		ft_write_str(2, "Error: invalid or unreachable PID\n");
		return (1);
	}
	g_can_write = 1;
	setup_signals();
	str = argv[2];
	i = 0;
	while (str[i] && g_can_write == 1)
		send_char(pid, (unsigned char)str[i++]);
	send_char(pid, '\0');
	return (0);
}
