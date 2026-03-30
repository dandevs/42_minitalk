/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   client.c                                           :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: danimend <danimend@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/03/30 03:47:57 by danimend          #+#    #+#             */
/*   Updated: 2026/03/30 03:51:24 by danimend         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <signal.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>

static volatile int	can_write;

static void	handler(int sig)
{
	if (sig == SIGUSR1)
		can_write = 1;
	else
		can_write = -1;
}

static void	send_char(pid_t pid, unsigned char c)
{
	int	bit;

	bit = 0;
	while (bit < 8 && can_write != -1)
	{
		can_write = 0;
		if (c & (1 << bit))
			kill(pid, SIGUSR1);
		else
			kill(pid, SIGUSR2);
		while (can_write == 0)
			pause();
		bit++;
	}
}

int	main(int argc, char **argv)
{
	pid_t	pid;
	char	*str;
	int		i;
	struct sigaction	sa;

	if (argc != 3)
	return (1);
	pid = atoi(argv[1]);
	can_write = 1;
	sa.sa_handler = handler;
	sigemptyset(&sa.sa_mask);
	sa.sa_flags = 0;

	sigaction(SIGUSR1, &sa, NULL);
	sigaction(SIGUSR2, &sa, NULL);

	str = argv[2];
	i = 0;
	while (str[i] && can_write == 1)
		send_char(pid, (unsigned char)str[i++]);
	send_char(pid, '\0');
	printf("\nCOMPLETED\n");
	return (0);
}
