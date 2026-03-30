/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   server.c                                           :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: danimend <danimend@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/03/30 03:47:56 by danimend          #+#    #+#             */
/*   Updated: 2026/03/30 09:14:24 by danimend         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <signal.h>
#include <unistd.h>
#include <stdio.h>
#include <sys/types.h>
#include "../shared/lib.h"

static volatile pid_t	g_active_pid;

static void	handler(int sig, siginfo_t *info, void *context)
{
	static int				bit = 0;
	static unsigned char	c = 0;
	int						done = 0;

	(void)context;
	if (!g_active_pid)
		g_active_pid = info->si_pid;
	else if (g_active_pid != info->si_pid)
		return ;
	if (sig == SIGUSR1)
		c |= (1 << bit);
	bit++;
	if (bit == 8)
	{
		if (c == '\0')
		{
			g_active_pid = 0;
			done = 1;
			kill(info->si_pid, SIGUSR2);
		}
		else
			write(1, &c, 1);
		c = 0;
		bit = 0;
	}
	if (!done)
		kill(info->si_pid, SIGUSR1);
}

int	main(void)
{
	struct sigaction	sa;

	sa.sa_sigaction = handler;
	sigemptyset(&sa.sa_mask);
	sa.sa_flags = SA_SIGINFO;
	sigaction(SIGUSR1, &sa, NULL);
	sigaction(SIGUSR2, &sa, NULL);
	ft_putnbr_fd(1, getpid());
	write(1, "\n", 1);
	while (1)
		pause();
	return (0);
}
