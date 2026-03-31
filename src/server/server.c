/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   server.c                                           :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: danimend <danimend@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/03/30 03:47:56 by danimend          #+#    #+#             */
/*   Updated: 2026/03/31 17:31:51 by danimend         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <signal.h>
#include <unistd.h>
#include <sys/types.h>
#include "../shared/lib.h"

static volatile pid_t	g_active_pid;

static int	is_same_client(pid_t client_pid, int *bit, unsigned char *c)
{
	if (!g_active_pid)
		g_active_pid = client_pid;
	else if (g_active_pid != client_pid && kill(g_active_pid, 0) == -1)
	{
		g_active_pid = client_pid;
		*bit = 0;
		*c = 0;
	}
	else if (g_active_pid != client_pid)
		return (0);
	return (1);
}

static void	process_received_char(unsigned char c, pid_t client_pid, int *done)
{
	if (c == '\0')
	{
		g_active_pid = 0;
		*done = 1;
		kill(client_pid, SIGUSR2);
	}
	else
		write(1, &c, 1);
}

static void	handler(int sig, siginfo_t *info, void *context)
{
	static int				bit = 0;
	static unsigned char	c = 0;
	int						done;

	(void)context;
	if (!is_same_client(info->si_pid, &bit, &c))
		return ;
	if (sig == SIGUSR1)
		c |= (1 << bit);
	bit++;
	done = 0;
	if (bit == 8)
	{
		process_received_char(c, info->si_pid, &done);
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
